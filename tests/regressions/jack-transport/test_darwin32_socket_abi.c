/* JACK-01E11A: source-only guest ABI probe; NEVER execute as a Linux client.
 * Darwin i386 ABI fields from darling-xnu pinned fa29287aa2f0:
 *   bsd/sys/socket.h, bsd/sys/un.h, bsd/sys/mman.h.
 * No system headers: can compile without Darwin SDK or i386 multilib.
 * Produces only a Mach-O relocatable object, not a runnable program.
 */

typedef unsigned char u8;
typedef unsigned short u16;
typedef unsigned int u32;
typedef unsigned long long u64;
typedef signed int i32;

#define DARWIN_AF_UNIX 1
#define DARWIN_SOCK_STREAM 1
#define DARWIN_SOL_SOCKET 0xffff
#define DARWIN_SCM_RIGHTS 1
#define DARWIN_MSG_TRUNC 0x10
#define DARWIN_MSG_CTRUNC 0x20
#define DARWIN_PROT_READ 1
#define DARWIN_PROT_WRITE 2
#define DARWIN_MAP_SHARED 1
#define PCM_MAGIC 0x314D4350u
#define FRAME_CAP 256u

struct darwin_sockaddr_un32 {
    u8 sun_len;
    u8 sun_family;
    char sun_path[104];
};
struct darwin_iovec32 { void *iov_base; u32 iov_len; };
struct darwin_msghdr32 {
    void *msg_name;
    u32 msg_namelen;
    struct darwin_iovec32 *msg_iov;
    i32 msg_iovlen;
    void *msg_control;
    u32 msg_controllen;
    i32 msg_flags;
};
struct darwin_cmsghdr32 {
    u32 cmsg_len;
    i32 cmsg_level;
    i32 cmsg_type;
};
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

_Static_assert(sizeof(void *) == 4, "must be i386");
_Static_assert(sizeof(struct darwin_sockaddr_un32) == 106, "Darwin sun path layout");
_Static_assert(__builtin_offsetof(struct darwin_sockaddr_un32, sun_path) == 2, "Darwin sun_len+family");
_Static_assert(sizeof(struct darwin_iovec32) == 8, "Darwin iovec32 size");
_Static_assert(sizeof(struct darwin_msghdr32) == 28, "Darwin msghdr32 size");
_Static_assert(sizeof(struct darwin_cmsghdr32) == 12, "Darwin cmsghdr32 size");
_Static_assert(_Alignof(SharedPCM) == 8, "SharedPCM alignment");
_Static_assert(sizeof(SharedPCM) == 64, "SharedPCM size");
_Static_assert(__builtin_offsetof(SharedPCM, read_frames) == 16, "read offset");
_Static_assert(__builtin_offsetof(SharedPCM, write_frames) == 24, "write offset");
_Static_assert(__builtin_offsetof(SharedPCM, state) == 40, "state offset");
_Static_assert(sizeof(SharedRegion) == 2112, "region size");

/* Freestanding deterministic zero-initialization; no implicit libc memset. */
__attribute__((used)) void *memset(void *dst, int value, u32 count)
{
    volatile u8 *p = (volatile u8 *)dst;
    for (u32 i = 0; i < count; ++i) p[i] = (u8)value;
    return dst;
}

/* Darwin userspace function declarations: actual runtime linkage UNQUALIFIED.
 * Import symbols are deliberately unresolved in this compile-only object. */
extern i32 socket(i32 domain, i32 type, i32 protocol);
extern i32 connect(i32 fd, const void *addr, u32 length);
extern i32 recvmsg(i32 fd, struct darwin_msghdr32 *msg, i32 flags);
extern void *mmap(void *addr, u32 size, i32 prot, i32 flags, i32 fd, long long offset);
extern i32 munmap(void *addr, u32 size);
extern i32 close(i32 fd);

/* Read-only header handshake candidate. NO PCM loop and NO ACK.
 * Do not run it against an active audio server: that would leave the server
 * waiting for a consumer. Later runtime tests need lifecycle coordination. */
i32 jack01e11_darwin32_socket_probe(const char *path)
{
    u32 path_length = 0;
    if (!path || path[0] != '/') return -1;
    while (path_length < 104 && path[path_length]) ++path_length;
    if (path_length == 0 || path_length >= 104) return -2;

    struct darwin_sockaddr_un32 address = {0};
    address.sun_len = (u8)(2 + path_length + 1);
    address.sun_family = DARWIN_AF_UNIX;
    for (u32 i = 0; i <= path_length; ++i) address.sun_path[i] = path[i];
    i32 s = socket(DARWIN_AF_UNIX, DARWIN_SOCK_STREAM, 0);
    if (s < 0) return -3;
    if (connect(s, &address, address.sun_len) != 0) { close(s); return -4; }

    char token = 0;
    struct darwin_iovec32 iov = {&token, 1};
    union { u32 align; u8 bytes[16]; } control = {0};
    struct darwin_msghdr32 msg = {0};
    msg.msg_iov = &iov;
    msg.msg_iovlen = 1;
    msg.msg_control = control.bytes;
    msg.msg_controllen = sizeof(control.bytes);
    if (recvmsg(s, &msg, 0) != 1 || token != 'F' ||
        (msg.msg_flags & (DARWIN_MSG_TRUNC | DARWIN_MSG_CTRUNC)) ||
        msg.msg_controllen < 16) { close(s); return -5; }
    const struct darwin_cmsghdr32 *cmsg = (const struct darwin_cmsghdr32 *)control.bytes;
    if (cmsg->cmsg_len != 16 || cmsg->cmsg_level != DARWIN_SOL_SOCKET ||
        cmsg->cmsg_type != DARWIN_SCM_RIGHTS) { close(s); return -6; }
    const i32 fd = *(const i32 *)(control.bytes + 12);
    if (fd < 0) { close(s); return -7; }

    SharedRegion *region = mmap(0, sizeof(SharedRegion),
                                DARWIN_PROT_READ | DARWIN_PROT_WRITE,
                                DARWIN_MAP_SHARED, fd, 0);
    close(fd);
    if (region == (void *)-1) { close(s); return -8; }
    const SharedPCM *h = &region->header;
    const i32 valid = h->magic == PCM_MAGIC && h->version == 1 && h->flags == 0 &&
                      h->capacity_frames == FRAME_CAP && h->channels == 2 &&
                      h->sample_rate == 48000 && h->format == 1;
    munmap(region, sizeof(SharedRegion));
    close(s);
    return valid ? 0 : -9;
}
