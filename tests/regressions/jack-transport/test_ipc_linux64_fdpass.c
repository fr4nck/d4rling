#define _GNU_SOURCE 1
#include <errno.h>
#include <fcntl.h>
#include <sched.h>
#include <signal.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <sys/socket.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <sys/un.h>
#include <time.h>
#include <unistd.h>

#define FRAME_CAP 256u
#define FRAME_TOTAL 50000u
#define IPC_MAGIC 0x314D4350u

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

_Static_assert(sizeof(SharedPCM) == 64, "header size");
_Static_assert(_Alignof(SharedPCM) == 8, "header alignment");
_Static_assert(offsetof(SharedPCM, read_frames) == 16, "rd offset");
_Static_assert(offsetof(SharedPCM, write_frames) == 24, "wr offset");
_Static_assert(offsetof(SharedPCM, state) == 40, "state offset");

typedef struct {
    SharedPCM header;
    float left[FRAME_CAP];
    float right[FRAME_CAP];
} SharedRegion;

static int push(SharedRegion *r, float left, float right)
{
    SharedPCM *h = &r->header;
    uint64_t w = __atomic_load_n(&h->write_frames, __ATOMIC_RELAXED);
    uint64_t rd = __atomic_load_n(&h->read_frames, __ATOMIC_ACQUIRE);
    if (w - rd >= FRAME_CAP) return 0;
    unsigned index = (unsigned)(w % FRAME_CAP);
    r->left[index] = left;
    r->right[index] = right;
    __atomic_store_n(&h->write_frames, w + 1, __ATOMIC_RELEASE);
    return 1;
}

static int pop(SharedRegion *r, float *left, float *right)
{
    SharedPCM *h = &r->header;
    uint64_t rd = __atomic_load_n(&h->read_frames, __ATOMIC_RELAXED);
    uint64_t w = __atomic_load_n(&h->write_frames, __ATOMIC_ACQUIRE);
    if (w == rd) {
        *left = 0.0f; *right = 0.0f;
        return 0;
    }
    unsigned index = (unsigned)(rd % FRAME_CAP);
    *left = r->left[index];
    *right = r->right[index];
    __atomic_store_n(&h->read_frames, rd + 1, __ATOMIC_RELEASE);
    return 1;
}

static int pass_fd(int socket_fd, int shared_fd)
{
    char token = 'F';
    struct iovec iov = { .iov_base = &token, .iov_len = 1 };
    union { struct cmsghdr align; unsigned char data[CMSG_SPACE(sizeof(int))]; } control;
    memset(&control, 0, sizeof(control));
    struct msghdr msg = {0};
    msg.msg_iov = &iov; msg.msg_iovlen = 1;
    msg.msg_control = control.data; msg.msg_controllen = sizeof(control.data);
    struct cmsghdr *cmsg = CMSG_FIRSTHDR(&msg);
    cmsg->cmsg_level = SOL_SOCKET;
    cmsg->cmsg_type = SCM_RIGHTS;
    cmsg->cmsg_len = CMSG_LEN(sizeof(int));
    memcpy(CMSG_DATA(cmsg), &shared_fd, sizeof(shared_fd));
    return sendmsg(socket_fd, &msg, 0) == 1 ? 0 : -1;
}

static int receive_fd(int socket_fd)
{
    char token = 0;
    struct iovec iov = { .iov_base = &token, .iov_len = 1 };
    union { struct cmsghdr align; unsigned char data[CMSG_SPACE(sizeof(int))]; } control;
    memset(&control, 0, sizeof(control));
    struct msghdr msg = {0};
    msg.msg_iov = &iov; msg.msg_iovlen = 1;
    msg.msg_control = control.data; msg.msg_controllen = sizeof(control.data);
    if (recvmsg(socket_fd, &msg, MSG_CMSG_CLOEXEC) != 1 || token != 'F' ||
        (msg.msg_flags & (MSG_CTRUNC | MSG_TRUNC))) return -1;
    struct cmsghdr *cmsg = CMSG_FIRSTHDR(&msg);
    if (!cmsg || cmsg->cmsg_level != SOL_SOCKET ||
        cmsg->cmsg_type != SCM_RIGHTS ||
        cmsg->cmsg_len != CMSG_LEN(sizeof(int))) return -1;
    int fd = -1;
    memcpy(&fd, CMSG_DATA(cmsg), sizeof(fd));
    return fd;
}

static int open_socket(const char *path)
{
    int s = socket(AF_UNIX, SOCK_STREAM | SOCK_CLOEXEC, 0);
    if (s < 0) return -1;
    struct sockaddr_un address = {0};
    address.sun_family = AF_UNIX;
    if (strlen(path) >= sizeof(address.sun_path)) {
        close(s); errno = ENAMETOOLONG; return -1;
    }
    strcpy(address.sun_path, path);
    if (bind(s, (struct sockaddr *)&address, sizeof(address)) || listen(s, 1)) {
        int saved = errno;
        close(s); errno = saved; return -1;
    }
    return s;
}

static int server(const char *path)
{
    alarm(20);
    signal(SIGPIPE, SIG_IGN);
    int s = open_socket(path);
    if (s < 0) { perror("socket/bind/listen"); return 2; }
    int fd = memfd_create("d4rling-jack01e8", MFD_CLOEXEC);
    if (fd < 0 || ftruncate(fd, sizeof(SharedRegion))) {
        perror("memfd/ftruncate");
        close(s); unlink(path); return 3;
    }
    SharedRegion *r = mmap(NULL, sizeof(*r), PROT_READ | PROT_WRITE,
                           MAP_SHARED, fd, 0);
    if (r == MAP_FAILED) {
        perror("server mmap"); close(fd); close(s); unlink(path); return 4;
    }
    memset(r, 0, sizeof(*r));
    SharedPCM *h = &r->header;
    h->magic = IPC_MAGIC; h->version = 1; h->capacity_frames = FRAME_CAP;
    h->channels = 2; h->sample_rate = 48000; h->format = 1;
    int conn = accept4(s, NULL, NULL, SOCK_CLOEXEC);
    if (conn < 0 || pass_fd(conn, fd)) {
        perror("server accept/pass_fd");
        if (conn >= 0) close(conn);
        munmap(r, sizeof(*r)); close(fd); close(s); unlink(path); return 5;
    }
    close(fd);
    for (unsigned i = 1; i <= FRAME_TOTAL; ) {
        if (!push(r, (float)i, -(float)i)) { sched_yield(); continue; }
        ++i;
    }
    char ack = 0;
    ssize_t n = recv(conn, &ack, 1, 0);
    uint64_t wr = __atomic_load_n(&h->write_frames, __ATOMIC_ACQUIRE);
    uint64_t rd = __atomic_load_n(&h->read_frames, __ATOMIC_ACQUIRE);
    unsigned state = __atomic_load_n(&h->state, __ATOMIC_ACQUIRE);
    int ok = n == 1 && ack == 'D' && wr == FRAME_TOTAL &&
             rd == FRAME_TOTAL && state == 2;
    printf("IPC_HEADER_SIZE=%zu\nIPC_PROCESS_COUNT=2\n", sizeof(*h));
    printf("IPC_SERVER_WRITE_FRAMES=%llu\n", (unsigned long long)wr);
    printf("IPC_SERVER_READ_FRAMES=%llu\n", (unsigned long long)rd);
    printf("IPC_SERVER_ACK=%s\n", ok ? "PASS" : "FAIL");
    printf("JACK01E8_SERVER_STATUS=%s\n", ok ? "PASS" : "FAIL");
    fflush(stdout);
    close(conn); munmap(r, sizeof(*r)); close(s); unlink(path);
    return ok ? 0 : 6;
}

static int client(const char *path)
{
    alarm(20);
    int s = socket(AF_UNIX, SOCK_STREAM | SOCK_CLOEXEC, 0);
    if (s < 0) { perror("client socket"); return 10; }
    struct sockaddr_un address = {0};
    address.sun_family = AF_UNIX;
    if (strlen(path) >= sizeof(address.sun_path)) {
        close(s); return 11;
    }
    strcpy(address.sun_path, path);
    struct timespec delay = { .tv_sec = 0, .tv_nsec = 10000000 };
    unsigned tries;
    for (tries = 0; tries < 200; ++tries) {
        if (!connect(s, (struct sockaddr *)&address, sizeof(address))) break;
        if (errno != ENOENT && errno != ECONNREFUSED) {
            perror("client connect"); close(s); return 12;
        }
        nanosleep(&delay, NULL);
    }
    if (tries == 200) { fprintf(stderr, "client connect timeout\n"); close(s); return 13; }
    int fd = receive_fd(s);
    if (fd < 0) { fprintf(stderr, "client did not receive memfd\n"); close(s); return 14; }
    struct stat st;
    if (fstat(fd, &st) || st.st_size != (off_t)sizeof(SharedRegion)) {
        fprintf(stderr, "client invalid memfd size\n");
        close(fd); close(s); return 15;
    }
    SharedRegion *r = mmap(NULL, sizeof(*r), PROT_READ | PROT_WRITE,
                           MAP_SHARED, fd, 0);
    close(fd);
    if (r == MAP_FAILED) { perror("client mmap"); close(s); return 16; }
    SharedPCM *h = &r->header;
    if (h->magic != IPC_MAGIC || h->version != 1 ||
        h->capacity_frames != FRAME_CAP || h->channels != 2 ||
        h->sample_rate != 48000 || h->format != 1) {
        fprintf(stderr, "client header mismatch\n");
        munmap(r, sizeof(*r)); close(s); return 17;
    }
    for (unsigned i = 1; i <= FRAME_TOTAL; ) {
        float x, y;
        if (!pop(r, &x, &y)) { sched_yield(); continue; }
        if (x != (float)i || y != -(float)i) {
            fprintf(stderr, "client sample mismatch at %u\n", i);
            munmap(r, sizeof(*r)); close(s); return 18;
        }
        ++i;
    }
    __atomic_store_n(&h->state, 2u, __ATOMIC_RELEASE);
    char ack = 'D';
    int sent = send(s, &ack, 1, MSG_NOSIGNAL) == 1;
    printf("IPC_CLIENT_RECEIVED_FD=YES\n");
    printf("IPC_CLIENT_READ_FRAMES=%u\n", FRAME_TOTAL);
    printf("JACK01E8_CLIENT_STATUS=%s\n", sent ? "PASS" : "FAIL");
    fflush(stdout);
    munmap(r, sizeof(*r)); close(s);
    return sent ? 0 : 19;
}

int main(int argc, char **argv)
{
    if (argc != 3 || argv[2][0] != '/') {
        fprintf(stderr, "usage: %s server|client /absolute/path.sock\n", argv[0]);
        return 1;
    }
    if (!strcmp(argv[1], "server")) return server(argv[2]);
    if (!strcmp(argv[1], "client")) return client(argv[2]);
    fprintf(stderr, "invalid mode\n");
    return 1;
}
