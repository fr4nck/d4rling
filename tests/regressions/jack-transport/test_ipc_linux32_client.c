/* JACK-01E10: libc-free ELF32 client for existing x86_64 Linux memfd server.
 * Test only. No Darling, CoreAudio, JACK or real-time safety guarantees.
 * Compiles with: clang-19 -m32 -march=i686 -std=c11 -O2 -nostdlib -static
 *   -fno-pie -ffreestanding -fno-builtin -fno-stack-protector
 *   -Wl,-e,_start -Wall -Wextra -Werror -o client source.c
 */

typedef unsigned int u32;
typedef unsigned short u16;
typedef unsigned long long u64;
typedef int i32;

#define FRAME_CAP 256u
#define FRAME_TOTAL 50000u
#define PCM_MAGIC 0x314D4350u
#define SOCK_PATH_LIMIT 108u

/* Linux i386 socketcall uses 32-bit user structures. */
struct sock_un32 { u16 family; char path[108]; };
struct iovec32 { void *base; u32 len; };
struct msghdr32 {
    void *name;
    u32 namelen;
    struct iovec32 *iov;
    u32 iovlen;
    void *control;
    u32 controllen;
    u32 flags;
};
struct cmsghdr32 { u32 len; i32 level; i32 type; };
struct timespec32 { i32 sec; i32 nsec; };

typedef struct {
    u32 magic;
    u16 version;
    u16 flags;
    u32 capacity_frames;
    u32 channels;
    _Alignas(8) u64 read_frames;
    _Alignas(8) u64 write_frames;
    u32 sample_rate;
    u32 format;
    u32 state;
    u32 reserved[5];
} SharedPCM;

typedef struct {
    SharedPCM header;
    float left[FRAME_CAP];
    float right[FRAME_CAP];
} SharedRegion;

_Static_assert(sizeof(void*) == 4, "ELF32 required");
_Static_assert(sizeof(struct msghdr32) == 28, "i386 msghdr ABI");
_Static_assert(sizeof(struct cmsghdr32) == 12, "i386 cmsghdr ABI");
_Static_assert(sizeof(struct sock_un32) == 110, "sockaddr_un ABI");
_Static_assert(_Alignof(SharedPCM) == 8, "shared header alignment");
_Static_assert(sizeof(SharedPCM) == 64, "shared header size");
_Static_assert(__builtin_offsetof(SharedPCM, read_frames) == 16, "rd offset");
_Static_assert(__builtin_offsetof(SharedPCM, write_frames) == 24, "wr offset");
_Static_assert(__builtin_offsetof(SharedPCM, state) == 40, "state offset");
_Static_assert(sizeof(SharedRegion) == 2112, "mapped region size");

/* Clang may synthesize memset for stack zero-initialization even freestanding. */
__attribute__((used)) void *memset(void *dst, int value, u32 size)
{
    volatile unsigned char *p = (volatile unsigned char *)dst;
    for (u32 i = 0; i < size; ++i) p[i] = (unsigned char)value;
    return dst;
}

static inline i32 syscall3(i32 nr, u32 a, u32 b, u32 c)
{
    i32 result;
    __asm__ volatile("int $0x80" : "=a"(result)
                     : "0"(nr), "b"(a), "c"(b), "d"(c)
                     : "memory", "cc");
    return result;
}
static inline i32 syscall2(i32 nr, u32 a, u32 b)
{
    return syscall3(nr, a, b, 0);
}
static inline i32 socketcall(u32 nr, u32 *args)
{
    return syscall2(102, nr, (u32)args);
}
static inline void *mmap_memfd(i32 fd)
{
    u32 out;
    /* Linux i386 __NR_mmap2=192; final page offset is EBP. */
    __asm__ volatile("pushl %%ebp\n\t"
                     "xorl %%ebp, %%ebp\n\t"
                     "int $0x80\n\t"
                     "popl %%ebp"
                     : "=a"(out)
                     : "0"(192), "b"(0), "c"((u32)sizeof(SharedRegion)),
                       "d"(3), "S"(1), "D"((u32)fd)
                     : "memory", "cc");
    return (void *)out;
}
static inline void write_text(u32 fd, const char *text)
{
    u32 n = 0;
    while (text[n]) ++n;
    (void)syscall3(4, fd, (u32)text, n);
}
static int fail(const char *message, i32 code)
{
    write_text(2, message);
    return code;
}
__attribute__((used)) static int client_main(i32 argc, char **argv)
{
    if (argc != 2) return fail("JACK01E10_FAIL=ARGUMENTS\n", 10);
    const char *path = argv[1];
    u32 len = 0;
    while (len < SOCK_PATH_LIMIT && path[len]) ++len;
    if (len == 0 || len >= SOCK_PATH_LIMIT || path[0] != '/')
        return fail("JACK01E10_FAIL=SOCKET_PATH\n", 11);

    (void)syscall2(27, 20, 0); /* alarm(20) bounds the guest test. */
    u32 sockargs[3] = {1, 1, 0}; /* AF_UNIX, SOCK_STREAM, protocol 0 */
    i32 sock = socketcall(1, sockargs);
    if (sock < 0) return fail("JACK01E10_FAIL=SOCKET\n", 12);
    struct sock_un32 address = {0};
    address.family = 1;
    for (u32 i = 0; i <= len; ++i) address.path[i] = path[i];
    u32 connargs[3] = {(u32)sock, (u32)&address, 2 + len + 1};
    struct timespec32 delay = {0, 10000000};
    i32 connected = 0;
    for (u32 tries = 0; tries != 200; ++tries) {
        i32 rc = socketcall(3, connargs);
        if (rc == 0) { connected = 1; break; }
        if (rc != -2 && rc != -111)
            return fail("JACK01E10_FAIL=CONNECT\n", 13);
        (void)syscall2(162, (u32)&delay, 0); /* nanosleep */
    }
    if (!connected) return fail("JACK01E10_FAIL=CONNECT_TIMEOUT\n", 14);

    char token = 0;
    struct iovec32 iov = {&token, 1};
    union {
        u32 alignment;
        unsigned char bytes[16];
    } control = {0};
    struct msghdr32 msg = {0};
    msg.iov = &iov;
    msg.iovlen = 1;
    msg.control = control.bytes;
    msg.controllen = sizeof(control.bytes);
    u32 recvargs[3] = {(u32)sock, (u32)&msg, 0x40000000u};
    i32 n = socketcall(17, recvargs); /* SYS_RECVMSG, MSG_CMSG_CLOEXEC */
    if (n != 1 || token != 'F' || (msg.flags & 0x28u) ||
        msg.controllen < sizeof(control.bytes))
        return fail("JACK01E10_FAIL=RECVMSG\n", 15);
    struct cmsghdr32 *cmsg = (struct cmsghdr32 *)control.bytes;
    if (cmsg->len != 16 || cmsg->level != 1 || cmsg->type != 1)
        return fail("JACK01E10_FAIL=ANCILLARY\n", 16);
    i32 fd = *(i32 *)(control.bytes + 12);
    if (fd < 0) return fail("JACK01E10_FAIL=BAD_FD\n", 17);
    i32 file_size = syscall3(19, (u32)fd, 0, 2); /* lseek(fd, 0, SEEK_END) */
    if (file_size != (i32)sizeof(SharedRegion))
        return fail("JACK01E10_FAIL=MEMFD_SIZE\n", 18);
    SharedRegion *region = (SharedRegion *)mmap_memfd(fd);
    (void)syscall2(6, (u32)fd, 0); /* close received fd */
    if ((u32)region >= 0xfffff001u)
        return fail("JACK01E10_FAIL=MMAP\n", 19);

    SharedPCM *h = &region->header;
    if (h->magic != PCM_MAGIC || h->version != 1 || h->flags != 0 ||
        h->capacity_frames != FRAME_CAP || h->channels != 2 ||
        h->sample_rate != 48000 || h->format != 1)
        return fail("JACK01E10_FAIL=HEADER\n", 20);

    for (u32 i = 1; i <= FRAME_TOTAL;) {
        u64 rd = __atomic_load_n(&h->read_frames, __ATOMIC_RELAXED);
        u64 wr = __atomic_load_n(&h->write_frames, __ATOMIC_ACQUIRE);
        if (wr == rd) {
            (void)syscall2(158, 0, 0); /* sched_yield, test only */
            continue;
        }
        if (wr < rd || wr - rd > FRAME_CAP)
            return fail("JACK01E10_FAIL=CURSORS\n", 21);
        u32 index = (u32)rd & (FRAME_CAP - 1);
        if (region->left[index] != (float)i ||
            region->right[index] != -(float)i)
            return fail("JACK01E10_FAIL=PCM_ORDER\n", 22);
        __atomic_store_n(&h->read_frames, rd + 1, __ATOMIC_RELEASE);
        ++i;
    }
    __atomic_store_n(&h->state, 2u, __ATOMIC_RELEASE);
    char ack = 'D';
    u32 sendargs[4] = {(u32)sock, (u32)&ack, 1, 0x4000u};
    if (socketcall(9, sendargs) != 1)
        return fail("JACK01E10_FAIL=ACK_SEND\n", 23);
    write_text(1, "IPC_ELF32_CLIENT_RECEIVED_FD=YES\n");
    write_text(1, "IPC_ELF32_READ_FRAMES=50000\n");
    write_text(1, "JACK01E10_CLIENT_STATUS=PASS_ELF32_MIXED_IPC\n");
    (void)syscall2(6, (u32)sock, 0);
    return 0;
}

__asm__(".global _start\n"
        "_start:\n"
        "  movl (%esp), %eax\n"
        "  leal 4(%esp), %edx\n"
        "  pushl %edx\n"
        "  pushl %eax\n"
        "  call client_main\n"
        "  movl %eax, %ebx\n"
        "  movl $1, %eax\n"
        "  int $0x80\n");
