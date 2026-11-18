/* R5 / ABI25 — atomicity of i386 side-storage accessors under concurrency (Mach-O i386/x86_64, MRR).
 *
 * Contract (Apple, "Programming with Objective-C", Atomic Properties): a getter of an atomic
 * property returns a whole value that stays valid for the caller even if another thread sets
 * the property at the same time. Witness objects (Tracked) are never freed: their memory stays a
 * tombstone, and any retain, release or message received after their last release is counted.
 *
 *   abi25-atomic race ITERATIONS     2 setter + 2 getter threads on NSMenuItem.view (retain)
 *                                     and NSCell.identifier (copy); prints ABI25_RACE ...
 *   abi25-atomic cost ITERATIONS     single-thread ns per getter / setter call
 */
#import <Foundation/Foundation.h>
#include <objc/runtime.h>
#include <pthread.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

@interface NSObject (ABI25API)
- (id) initWithTitle: (NSString *) t action: (SEL) a keyEquivalent: (NSString *) k;
- (id) initTextCell: (NSString *) s;
- (void) setView: (id) v;
- (id) view;
- (void) setIdentifier: (id) v;
- (id) identifier;
@end

static volatile long gCreated, gDead, gRetainAfter, gReleaseAfter, gTouchAfter;

@interface Tracked : NSObject {
  @public
    volatile long rc;
    volatile long dead;
}
+ (id) tracked;
- (long) touch;
@end

@implementation Tracked
+ (id) tracked {
    Tracked *t = [self alloc];
    t->rc = 1;
    __sync_fetch_and_add(&gCreated, 1);
    return t;
}
- (id) retain {
    if (__sync_fetch_and_add(&rc, 0) <= 0 || dead) __sync_fetch_and_add(&gRetainAfter, 1);
    __sync_fetch_and_add(&rc, 1);
    return self;
}
- (oneway void) release {
    if (dead) { __sync_fetch_and_add(&gReleaseAfter, 1); return; }
    if (__sync_sub_and_fetch(&rc, 1) == 0) { dead = 1; __sync_fetch_and_add(&gDead, 1); }
}
- (NSUInteger) retainCount { return (NSUInteger) rc; }
- (id) copyWithZone: (NSZone *) z { (void) z; return [self retain]; }
- (id) copy { return [self retain]; }
- (long) touch { if (dead) __sync_fetch_and_add(&gTouchAfter, 1); return rc; }
- (void) dealloc { printf("ABI25_UNEXPECTED_DEALLOC\n"); }
@end

static id gItem, gCell;
static long gIters;

static void *setter(void *arg) {
    int which = (int) (long) arg;
    for (long i = 0; i < gIters; i++) {
        Tracked *t = [Tracked tracked];
        if (which) [gCell setIdentifier: t]; else [gItem setView: t];
        [t release];
    }
    return NULL;
}

static void *getter(void *arg) {
    int which = (int) (long) arg;
    NSAutoreleasePool *pool = [[NSAutoreleasePool alloc] init];
    for (long i = 0; i < gIters; i++) {
        id v = which ? [gCell identifier] : [gItem view];
        [v retain];
        [v touch];
        [v release];
        if ((i & 255) == 255) { [pool drain]; pool = [[NSAutoreleasePool alloc] init]; }
    }
    [pool drain];
    return NULL;
}

static double now(void) {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return ts.tv_sec + ts.tv_nsec / 1e9;
}

int main(int argc, char **argv) {
    setvbuf(stdout, NULL, _IONBF, 0);
    NSAutoreleasePool *pool = [[NSAutoreleasePool alloc] init];
    if (argc != 3 || (strcmp(argv[1], "race") && strcmp(argv[1], "cost"))) {
        fprintf(stderr, "usage: abi25-atomic race|cost ITERATIONS\n");
        return 2;
    }
    gIters = atol(argv[2]);
    Class mi = objc_getClass("NSMenuItem"), ce = objc_getClass("NSCell");
    if (!mi || !ce) { printf("ABI25_FATAL class_not_found\n"); return 3; }
    gItem = [[mi alloc] initWithTitle: @"abi25" action: NULL keyEquivalent: @""];
    gCell = [[ce alloc] initTextCell: @"abi25"];
    printf("ABI25 PTR=%d item=%s cell=%s\n", (int) (sizeof(void *) * 8), class_getName(object_getClass(gItem)), class_getName(object_getClass(gCell)));

    if (!strcmp(argv[1], "cost")) {
        Tracked *t = [Tracked tracked];
        [gItem setView: t];
        double t0 = now();
        for (long i = 0; i < gIters; i++) { NSAutoreleasePool *p = [[NSAutoreleasePool alloc] init]; [gItem view]; [p drain]; }
        double t1 = now();
        for (long i = 0; i < gIters; i++) [gItem setView: t];
        double t2 = now();
        double t3 = now();
        for (long i = 0; i < gIters; i++) { NSAutoreleasePool *p = [[NSAutoreleasePool alloc] init]; [p drain]; }
        double t4 = now();
        [gItem setView: nil];
        [t release];
        printf("ABI25_COST getter_ns=%.1f setter_ns=%.1f pool_only_ns=%.1f iterations=%ld\n",
               (t1 - t0) * 1e9 / gIters, (t2 - t1) * 1e9 / gIters, (t4 - t3) * 1e9 / gIters, gIters);
        return 0;
    }

    pthread_t th[4];
    pthread_create(&th[0], NULL, setter, (void *) 0L);
    pthread_create(&th[1], NULL, getter, (void *) 0L);
    pthread_create(&th[2], NULL, setter, (void *) 1L);
    pthread_create(&th[3], NULL, getter, (void *) 1L);
    for (int i = 0; i < 4; i++) pthread_join(th[i], NULL);

    [gItem setView: nil];
    [gCell setIdentifier: nil];
    [pool drain];
    long leaked = gCreated - gDead;
    printf("ABI25_RACE iterations=%ld created=%ld dead=%ld leaked=%ld retain_after_dealloc=%ld release_after_dealloc=%ld touch_after_dealloc=%ld\n",
           gIters, gCreated, gDead, leaked, gRetainAfter, gReleaseAfter, gTouchAfter);
    return (gRetainAfter || gReleaseAfter || gTouchAfter || leaked) ? 1 : 0;
}
