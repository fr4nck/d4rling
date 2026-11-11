#pragma once
#include <malloc.h>
static inline size_t malloc_size(void* ptr) { return malloc_usable_size(ptr); }
