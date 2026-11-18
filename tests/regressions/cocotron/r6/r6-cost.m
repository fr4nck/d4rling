/* R6 — cost of AppKit extras accesses (Mach-O, MRR): a plain method reading an extra field
 * (-[NSMenuItem tag]), an atomic getter and setter (-view / -setView:). ns per call. */
#import <Foundation/Foundation.h>
#include <objc/runtime.h>
#include <stdio.h>
#include <stdlib.h>
#include <time.h>
@interface NSObject (R6Cost)
- (id) initWithTitle: (NSString *) t action: (SEL) a keyEquivalent: (NSString *) k;
- (NSInteger) tag; - (void) setView: (id) v; - (id) view;
@end
static double now(void) { struct timespec t; clock_gettime(CLOCK_MONOTONIC, &t); return t.tv_sec + t.tv_nsec / 1e9; }
int main(int argc, char **argv) {
    long n = argc > 1 ? atol(argv[1]) : 1000000;
    NSAutoreleasePool *pool = [[NSAutoreleasePool alloc] init];
    id item = [[objc_getClass("NSMenuItem") alloc] initWithTitle: @"r6" action: NULL keyEquivalent: @""];
    if (!item) { printf("R6_COST_FATAL\n"); return 3; }
    id v = [[NSObject alloc] init];
    [item setView: v];
    volatile long sink = 0;
    double t0 = now(); for (long i = 0; i < n; i++) sink += [item tag];
    double t1 = now(); for (long i = 0; i < n; i++) [item setView: v];
    double t2 = now(); for (long i = 0; i < n; i++) { NSAutoreleasePool *p = [[NSAutoreleasePool alloc] init]; (void) [item view]; [p drain]; }
    double t3 = now(); for (long i = 0; i < n; i++) { NSAutoreleasePool *p = [[NSAutoreleasePool alloc] init]; [p drain]; }
    double t4 = now();
    printf("R6_COST ptr=%d tag_ns=%.1f setter_ns=%.1f getter_ns=%.1f pool_ns=%.1f getter_minus_pool_ns=%.1f n=%ld\n",
           (int) (sizeof(void *) * 8), (t1 - t0) * 1e9 / n, (t2 - t1) * 1e9 / n, (t3 - t2) * 1e9 / n,
           (t4 - t3) * 1e9 / n, ((t3 - t2) - (t4 - t3)) * 1e9 / n, n);
    return 0;
}
