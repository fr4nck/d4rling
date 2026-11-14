/* Native bench only: count and fail QuickTime.c allocations (same contract as
 * the E3 host adapter used by the quicktime-tracks / mov-pcm witnesses). */
#include <stdlib.h>
void *d4rl_test_malloc(size_t size);
void d4rl_test_free(void *ptr);
#define malloc d4rl_test_malloc
#define free d4rl_test_free
