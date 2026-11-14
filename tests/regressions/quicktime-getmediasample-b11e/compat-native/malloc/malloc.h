#ifndef D4RL_MM_NATIVE_MALLOC
#define D4RL_MM_NATIVE_MALLOC
#include <stddef.h>
#include <malloc.h>
static inline size_t malloc_size(const void *p)
{
    return p ? malloc_usable_size((void *)p) : 0;
}
#endif
