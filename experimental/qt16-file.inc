
#ifndef D4RL_QT_FILE_BACKEND
#define D4RL_QT_FILE_BACKEND

#include <stdint.h>
#include <stdlib.h>
#include <unistd.h>
#include <fcntl.h>
#include <errno.h>
#include <sys/types.h>
#include <sys/stat.h>

enum {
    QF_OK = 0,
    QF_PARAM = -50,
    QF_BADREF = -51,
    QF_NOTFOUND = -43,
    QF_PERMISSION = -54,
    QF_IO = -36,
    QF_MEMORY = -108,
    QF_UNIMPLEMENTED = -4,
    QF_EOF = -39,
    QF_LIMIT = -42
};

#define QF_SLOTS 64
#define QF_MAX_BYTES (128UL * 1024UL * 1024UL)

struct qf_slot {
    int used;
    int fd;
    short ref;
};

static struct qf_slot qf_slots[QF_SLOTS];
static unsigned qf_next = 1000;

static struct qf_slot *qf_find(short ref)
{
    for(unsigned i=0;i<QF_SLOTS;++i)
        if(qf_slots[i].used &&
           qf_slots[i].ref==ref)
            return &qf_slots[i];

    return NULL;
}

static short qf_open(const char *path,short *out)
{
    if(!path || !*path || !out)
        return QF_PARAM;

    struct qf_slot *slot=NULL;

    for(unsigned i=0;i<QF_SLOTS;++i)
        if(!qf_slots[i].used) {
            slot=&qf_slots[i];
            break;
        }

    if(!slot || qf_next>32767)
        return QF_LIMIT;

    int fd=open(path,O_RDONLY|O_NONBLOCK|O_CLOEXEC);

    if(fd<0) {
        if(errno==ENOENT || errno==ENOTDIR)
            return QF_NOTFOUND;

        if(errno==EACCES || errno==EPERM)
            return QF_PERMISSION;

        return QF_IO;
    }

    struct stat st;

    if(fstat(fd,&st) || !S_ISREG(st.st_mode)) {
        close(fd);
        return QF_PARAM;
    }

    if(st.st_size<0 ||
       (uint64_t)st.st_size>QF_MAX_BYTES) {
        close(fd);
        return QF_LIMIT;
    }

    slot->fd=fd;
    slot->ref=(short)qf_next++;
    slot->used=1;

    *out=slot->ref;

    return QF_OK;
}

static short qf_read(short ref,
                     unsigned char **out,
                     int32_t *length)
{
    if(!out || !length)
        return QF_PARAM;

    struct qf_slot *slot=qf_find(ref);

    if(!slot)
        return QF_BADREF;

    struct stat st;

    if(fstat(slot->fd,&st))
        return QF_IO;

    if(st.st_size<=0)
        return QF_EOF;

    if((uint64_t)st.st_size>QF_MAX_BYTES)
        return QF_LIMIT;

    size_t n=(size_t)st.st_size;

    unsigned char *data=malloc(n);

    if(!data)
        return QF_MEMORY;

    size_t total=0;

    while(total<n) {
        ssize_t got=pread(
            slot->fd,data+total,n-total,
            (off_t)total
        );

        if(got<0 && errno==EINTR)
            continue;

        if(got<=0) {
            free(data);
            return got==0?QF_EOF:QF_IO;
        }

        total+=(size_t)got;
    }

    *out=data;
    *length=(int32_t)n;

    return QF_OK;
}

static short qf_close(short ref)
{
    struct qf_slot *slot=qf_find(ref);

    if(!slot)
        return QF_BADREF;

    int fd=slot->fd;

    slot->used=0;
    slot->ref=0;
    slot->fd=-1;

    return close(fd)==0?QF_OK:QF_IO;
}

#endif
