#ifndef D4RLING_PRIVATE_ATOMIC_BRIDGE
#define D4RLING_PRIVATE_ATOMIC_BRIDGE

#include <stdatomic.h>

#ifndef __clang__
#error "This bridge requires Clang"
#endif

#ifndef atomic_init
#define atomic_init(obj, val) \
    __c11_atomic_init((obj), (val))
#endif

#ifndef atomic_load_explicit
#define atomic_load_explicit(obj, order) \
    __c11_atomic_load((obj), (order))
#endif

#ifndef atomic_compare_exchange_weak_explicit
#define atomic_compare_exchange_weak_explicit(obj, expected, desired, success, failure) \
    __c11_atomic_compare_exchange_weak((obj), (expected), (desired), (success), (failure))
#endif

#ifndef atomic_fetch_sub_explicit
#define atomic_fetch_sub_explicit(obj, val, order) \
    __c11_atomic_fetch_sub((obj), (val), (order))
#endif

#ifndef memory_order_relaxed
#define memory_order_relaxed __ATOMIC_RELAXED
#endif

#ifndef memory_order_acq_rel
#define memory_order_acq_rel __ATOMIC_ACQ_REL
#endif

#endif
