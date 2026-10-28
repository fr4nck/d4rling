#define _GNU_SOURCE 1
#include <errno.h>
#include <sched.h>
#include <signal.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <unistd.h>

#define RING_CAP 256u
#define FRAME_COUNT 50000u
#define PCM_MAGIC 0x314D4350u

typedef struct {
    uint32_t magic;
    uint16_t version;
    uint16_t flags;
    uint32_t capacity_frames;
    uint32_t channels;
    _Alignas(8) uint64_t read_frames;
    _Alignas(8) uint64_t write_frames;
    uint32_t sample_rate;
    uint32_t format;
    uint32_t state;
    uint32_t reserved[5];
} SharedPCM;

_Static_assert(sizeof(SharedPCM) == 64, "header must be 64 bytes");
_Static_assert(_Alignof(SharedPCM) == 8, "header alignment");
_Static_assert(offsetof(SharedPCM, read_frames) == 16, "read offset");
_Static_assert(offsetof(SharedPCM, write_frames) == 24, "write offset");
_Static_assert(offsetof(SharedPCM, state) == 40, "state offset");

typedef struct {
    SharedPCM header;
    float left[RING_CAP];
    float right[RING_CAP];
} SharedRegion;

static int try_write(SharedRegion *region, float left, float right)
{
    SharedPCM *h = &region->header;
    uint64_t write_at = __atomic_load_n(&h->write_frames, __ATOMIC_RELAXED);
    uint64_t read_at = __atomic_load_n(&h->read_frames, __ATOMIC_ACQUIRE);
    if (write_at - read_at >= RING_CAP)
        return 0;
    unsigned index = (unsigned)(write_at % RING_CAP);
    region->left[index] = left;
    region->right[index] = right;
    __atomic_store_n(&h->write_frames, write_at + 1, __ATOMIC_RELEASE);
    return 1;
}

static int try_read(SharedRegion *region, float *left, float *right)
{
    SharedPCM *h = &region->header;
    uint64_t read_at = __atomic_load_n(&h->read_frames, __ATOMIC_RELAXED);
    uint64_t write_at = __atomic_load_n(&h->write_frames, __ATOMIC_ACQUIRE);
    if (write_at == read_at) {
        *left = 0.0f;
        *right = 0.0f;
        return 0;
    }
    unsigned index = (unsigned)(read_at % RING_CAP);
    *left = region->left[index];
    *right = region->right[index];
    __atomic_store_n(&h->read_frames, read_at + 1, __ATOMIC_RELEASE);
    return 1;
}

int main(void)
{
    SharedRegion *region = mmap(NULL, sizeof(*region), PROT_READ | PROT_WRITE,
                                MAP_SHARED | MAP_ANONYMOUS, -1, 0);
    if (region == MAP_FAILED) {
        perror("mmap");
        return 2;
    }
    SharedPCM *h = &region->header;
    h->magic = PCM_MAGIC;
    h->version = 1;
    h->capacity_frames = RING_CAP;
    h->channels = 2;
    h->sample_rate = 48000;
    h->format = 1;

    float x = -1.0f, y = -1.0f;
    if (try_read(region, &x, &y) != 0 || x != 0.0f || y != 0.0f) {
        fprintf(stderr, "FAIL: empty queue did not return silence\n");
        munmap(region, sizeof(*region));
        return 3;
    }
    for (unsigned i = 0; i < RING_CAP; ++i)
        if (!try_write(region, (float)i, (float)-(int)i)) {
            fprintf(stderr, "FAIL: queue prefill\n");
            munmap(region, sizeof(*region));
            return 4;
        }
    if (try_write(region, 1.0f, 2.0f)) {
        fprintf(stderr, "FAIL: queue overflow was accepted\n");
        munmap(region, sizeof(*region));
        return 5;
    }
    for (unsigned i = 0; i < RING_CAP; ++i)
        if (!try_read(region, &x, &y) || x != (float)i || y != (float)-(int)i) {
            fprintf(stderr, "FAIL: preflight wrapped data\n");
            munmap(region, sizeof(*region));
            return 6;
        }
    __atomic_store_n(&h->read_frames, 0, __ATOMIC_RELAXED);
    __atomic_store_n(&h->write_frames, 0, __ATOMIC_RELAXED);

    pid_t pid = fork();
    if (pid < 0) {
        perror("fork");
        munmap(region, sizeof(*region));
        return 7;
    }
    if (pid == 0) {
        alarm(15);
        if (h->magic != PCM_MAGIC || h->version != 1 ||
            h->capacity_frames != RING_CAP || h->channels != 2 ||
            h->sample_rate != 48000)
            _exit(10);
        for (unsigned i = 1; i <= FRAME_COUNT; ) {
            if (!try_read(region, &x, &y)) {
                sched_yield();
                continue;
            }
            if (x != (float)i || y != -(float)i)
                _exit(11);
            ++i;
        }
        __atomic_store_n(&h->state, 2u, __ATOMIC_RELEASE);
        _exit(0);
    }

    alarm(20);
    for (unsigned i = 1; i <= FRAME_COUNT; ) {
        if (!try_write(region, (float)i, -(float)i)) {
            sched_yield();
            continue;
        }
        ++i;
    }
    int status = 0;
    if (waitpid(pid, &status, 0) != pid) {
        perror("waitpid");
        munmap(region, sizeof(*region));
        return 8;
    }
    const uint64_t wr = __atomic_load_n(&h->write_frames, __ATOMIC_ACQUIRE);
    const uint64_t rd = __atomic_load_n(&h->read_frames, __ATOMIC_ACQUIRE);
    const unsigned state = __atomic_load_n(&h->state, __ATOMIC_ACQUIRE);
    const int ok = WIFEXITED(status) && WEXITSTATUS(status) == 0 &&
                   wr == FRAME_COUNT && rd == FRAME_COUNT && state == 2;
    printf("IPC_HEADER_SIZE=%zu\n", sizeof(*h));
    printf("IPC_FRAME_COUNT=%u\n", FRAME_COUNT);
    printf("IPC_READ_FRAMES=%llu\n", (unsigned long long)rd);
    printf("IPC_WRITE_FRAMES=%llu\n", (unsigned long long)wr);
    printf("IPC_CHANNELS=%u\n", h->channels);
    printf("IPC_PROCESS_COUNT=2\n");
    printf("IPC_CHILD_STATUS=%d\n", WIFEXITED(status) ? WEXITSTATUS(status) : -1);
    printf("JACK01E7_STATUS=%s\n", ok ? "PASS_IPC_LINUX64_TWO_PROCESSES" : "FAIL_IPC");
    printf("MACHO_RUNTIME=NOT_EXECUTED\nREAL_JACK_TEST=NOT_EXECUTED\n");
    munmap(region, sizeof(*region));
    return ok ? 0 : 9;
}
