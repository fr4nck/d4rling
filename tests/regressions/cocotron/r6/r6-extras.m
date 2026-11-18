/* R6 — AppKitIvarLayout.h extras under concurrency, in the real Darwin runtime (Mach-O i386, MRR).
 * Complements ABI26-R2 (atomic-accessors-runtime.m): it covers the cases R2 leaves open.
 * Compiled against the candidate header under test (-I its directory); no AppKit code is used,
 * the macros under test are inline in this witness. Values are Tracked tombstones: never freed,
 * they count retain/release/messages received after their last release.
 *
 *   r6-extras first N  ptr|side   N fresh objects, 4 threads race the first use of the extras
 *                                  (block publication), each setting its own value; afterwards
 *                                  exactly one value must be held, the others released once.
 *   r6-extras destroy N ptr|side  a reader gets the value, the container is then released by
 *                                  another thread; the value must stay alive until the reader's
 *                                  autorelease pool drains (getter ownership across -dealloc).
 *   r6-extras copy N ptr|side     2 readers spin on the getter while the main thread makes and
 *                                  releases copies (NSCopyObject + NS_EXTRA_COPY + retained value,
 *                                  the R22 pattern); every value is released exactly once.
 * Prints R6_RESULT ... and returns 1 on any anomaly.
 */
#import <Foundation/Foundation.h>
#import "AppKitIvarLayout.h"
#include <pthread.h>
#include <sched.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static volatile long gCreated, gDead, gRetainAfter, gReleaseAfter, gTouchAfter, gMismatch;

@interface Tracked : NSObject {
  @public
    volatile long rc, dead;
}
+ (id) tracked;
- (long) touch;
@end
@implementation Tracked
+ (id) tracked { Tracked *t = [self alloc]; t->rc = 1; __sync_fetch_and_add(&gCreated, 1); return t; }
- (id) retain { if (dead) __sync_fetch_and_add(&gRetainAfter, 1); __sync_fetch_and_add(&rc, 1); return self; }
- (oneway void) release {
    if (dead) { __sync_fetch_and_add(&gReleaseAfter, 1); return; }
    if (__sync_sub_and_fetch(&rc, 1) == 0) { dead = 1; __sync_fetch_and_add(&gDead, 1); }
}
- (NSUInteger) retainCount { return (NSUInteger) rc; }
- (id) copyWithZone: (NSZone *) z { (void) z; return [self retain]; }
- (long) touch { if (dead) __sync_fetch_and_add(&gTouchAfter, 1); return rc; }
- (void) dealloc { printf("R6_UNEXPECTED_DEALLOC\n"); }
@end

#define R6_CLASS(cls, END)                                                       \
@interface cls : NSObject <NSCopying> {                                         \
    NS_EXTRA_IVARS_BEGIN(cls)                                                   \
        id _value;                                                              \
        long _n;                                                                \
    END(cls)                                                                    \
}                                                                               \
@property(retain) id value;                                                     \
@property long n;                                                               \
@end                                                                            \
@implementation cls                                                             \
NS_EXTRA_SYNTHESIZE_RETAIN(cls, value, _value, id, value, setValue:)            \
NS_EXTRA_SYNTHESIZE_ASSIGN(cls, n, _n, long, n, setN:)                          \
- (id) copyWithZone: (NSZone *) zone {                                          \
    cls *copy = NSCopyObject(self, 0, zone);                                    \
    NS_EXTRA_COPY(cls, copy, self);                                             \
    NS_EXTRA(cls, copy)->_value = [[self value] retain];                        \
    return copy;                                                                \
}                                                                               \
- (void) dealloc {                                                              \
    if (NS_EXTRA_ALLOCATED(cls, self)) [NS_EXTRA(cls, self)->_value release];   \
    NS_EXTRA_FREE(cls, self);                                                   \
    [super dealloc];                                                            \
}                                                                               \
@end

#if __OBJC2__
#define R6_PTR_END NS_EXTRA_IVARS_END
#define R6_SIDE_END NS_EXTRA_IVARS_END
#else
#define R6_PTR_END NS_EXTRA_IVARS_END
#define R6_SIDE_END NS_SIDE_IVARS_END
#endif
R6_CLASS(R6Ptr, R6_PTR_END)
R6_CLASS(R6Side, R6_SIDE_END)

enum { THREADS = 4 };
static Class gClass;
static id volatile gObj;
static volatile long gGen, gDone, gGot, gReleased;
static long gIters;
static const char *gMode;

static void spin_until(volatile long *v, long target) { while (__atomic_load_n(v, __ATOMIC_ACQUIRE) < target) sched_yield(); }

static void *first_worker(void *arg) {
    long me = (long) arg;
    for (long g = 1; g <= gIters; g++) {
        spin_until(&gGen, g);
        NSAutoreleasePool *pool = [[NSAutoreleasePool alloc] init];
        Tracked *t = [Tracked tracked];
        [gObj setValue: t];
        [gObj setN: me + 1];
        [t release];
        [pool drain];
        __atomic_fetch_add(&gDone, 1, __ATOMIC_ACQ_REL);
    }
    return NULL;
}

static void *destroy_reader(void *arg) {
    (void) arg;
    for (long g = 1; g <= gIters; g++) {
        spin_until(&gGen, g);
        NSAutoreleasePool *pool = [[NSAutoreleasePool alloc] init];
        id v = [gObj value];
        __atomic_store_n(&gGot, g, __ATOMIC_RELEASE);
        spin_until(&gReleased, g);
        [v touch];                 /* the container is gone: v must still be alive */
        [pool drain];
        __atomic_store_n(&gDone, g, __ATOMIC_RELEASE);
    }
    return NULL;
}

static volatile int gStopReaders;
static void *copy_reader(void *arg) {
    (void) arg;
    while (!__atomic_load_n(&gStopReaders, __ATOMIC_ACQUIRE)) {
        NSAutoreleasePool *pool = [[NSAutoreleasePool alloc] init];
        id v = [gObj value];
        [v retain]; [v touch]; [v release];
        (void) [gObj n];
        [pool drain];
    }
    return NULL;
}

int main(int argc, char **argv) {
    setvbuf(stdout, NULL, _IONBF, 0);
    if (argc != 4) { fprintf(stderr, "usage: r6-extras first|destroy|copy N ptr|side\n"); return 2; }
    gMode = argv[1]; gIters = atol(argv[2]);
    gClass = !strcmp(argv[3], "side") ? [R6Side class] : [R6Ptr class];
    NSAutoreleasePool *pool = [[NSAutoreleasePool alloc] init];
    pthread_t th[THREADS];
    long objects = 0;

    if (!strcmp(gMode, "first")) {
        for (long i = 0; i < THREADS; i++) pthread_create(&th[i], NULL, first_worker, (void *) i);
        for (long g = 1; g <= gIters; g++) {
            id obj = [[gClass alloc] init];           /* -init does not touch the extras */
            gObj = obj;
            __atomic_store_n(&gGen, g, __ATOMIC_RELEASE);
            spin_until(&gDone, g * THREADS);
            long held = 0;
            id v = [obj value];                         /* atomic getter: retained+autoreleased */
            if (v) held = ((Tracked *) v)->rc;
            long n = [obj n];
            /* the held value: our temporary reference + the object's one */
            if (!v || ((Tracked *) v)->dead || held < 1 || n < 1 || n > THREADS)
                __sync_fetch_and_add(&gMismatch, 1);
            [obj release];
            objects++;
            if ((g & 63) == 0) { [pool drain]; pool = [[NSAutoreleasePool alloc] init]; }
        }
        for (int i = 0; i < THREADS; i++) pthread_join(th[i], NULL);
    } else if (!strcmp(gMode, "destroy")) {
        pthread_create(&th[0], NULL, destroy_reader, NULL);
        for (long g = 1; g <= gIters; g++) {
            id obj = [[gClass alloc] init];
            Tracked *t = [Tracked tracked];
            [obj setValue: t];
            [t release];
            gObj = obj;
            __atomic_store_n(&gGen, g, __ATOMIC_RELEASE);
            spin_until(&gGot, g);
            [obj release];                              /* -dealloc releases the value */
            __atomic_store_n(&gReleased, g, __ATOMIC_RELEASE);
            spin_until(&gDone, g);
            objects++;
        }
        pthread_join(th[0], NULL);
    } else if (!strcmp(gMode, "copy")) {
        id obj = [[gClass alloc] init];
        Tracked *t = [Tracked tracked];
        [obj setValue: t];
        [obj setN: 7];
        [t release];
        gObj = obj;
        for (int i = 0; i < 2; i++) pthread_create(&th[i], NULL, copy_reader, NULL);
        for (long g = 0; g < gIters; g++) {
            id c = [obj copy];
            if ([c value] != t || [c n] != 7) __sync_fetch_and_add(&gMismatch, 1);
            [c release];
            if ((g & 63) == 0) { [pool drain]; pool = [[NSAutoreleasePool alloc] init]; }
        }
        __atomic_store_n(&gStopReaders, 1, __ATOMIC_RELEASE);
        for (int i = 0; i < 2; i++) pthread_join(th[i], NULL);
        [pool drain]; pool = [[NSAutoreleasePool alloc] init];
        [obj release];
        objects = 1;
    } else {
        return 2;
    }
    [pool drain];
    long leaked = gCreated - gDead;
    int bad = gRetainAfter || gReleaseAfter || gTouchAfter || gMismatch || leaked;
    printf("R6_RESULT mode=%s class=%s ptr_bits=%d iterations=%ld objects=%ld created=%ld dead=%ld leaked=%ld "
           "retain_after=%ld release_after=%ld touch_after=%ld mismatch=%ld verdict=%s\n",
           gMode, class_getName(gClass), (int) (sizeof(void *) * 8), gIters, objects, gCreated, gDead, leaked,
           gRetainAfter, gReleaseAfter, gTouchAfter, gMismatch, bad ? "FAIL" : "PASS");
    return bad ? 1 : 0;
}
