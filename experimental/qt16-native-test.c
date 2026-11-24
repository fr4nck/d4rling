
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include "qt16-file.inc"

#define CHECK(x) do { \
    if(!(x)) { \
        printf("FAIL line=%d %s\n",__LINE__,#x); \
        return 1; \
    } \
    ++checks; \
} while(0)

int main(int argc,char **argv)
{
    unsigned checks=0;

    CHECK(argc==6);

    const char *file=argv[1];
    const char *missing=argv[2];
    const char *empty=argv[3];
    const char *fifo=argv[4];
    const char *oversize=argv[5];

    short a=-1,b=-1;
    unsigned char *data=NULL;
    int32_t length=0;

    CHECK(qf_open(NULL,&a)==QF_PARAM);
    CHECK(a==-1);
    CHECK(qf_open(file,NULL)==QF_PARAM);
    CHECK(qf_open(missing,&a)==QF_NOTFOUND);
    CHECK(a==-1);
    CHECK(qf_open(fifo,&a)==QF_PARAM);
    CHECK(qf_open("/tmp",&a)==QF_PARAM);
    CHECK(qf_open(oversize,&a)==QF_LIMIT);
    CHECK(qf_close(-1)==QF_BADREF);

    CHECK(qf_open(file,&a)==QF_OK);
    CHECK(qf_open(file,&b)==QF_OK);
    CHECK(a!=b);

    CHECK(qf_read(a,&data,&length)==QF_OK);
    CHECK(length==8);
    CHECK(memcmp(data,"D4RLQT16",8)==0);
    free(data);

    CHECK(qf_close(a)==QF_OK);
    CHECK(qf_close(a)==QF_BADREF);

    data=NULL;
    length=-1;

    CHECK(qf_read(a,&data,&length)==QF_BADREF);
    CHECK(data==NULL && length==-1);

    CHECK(qf_read(b,&data,&length)==QF_OK);
    CHECK(length==8);
    CHECK(memcmp(data,"D4RLQT16",8)==0);
    free(data);

    CHECK(qf_close(b)==QF_OK);

    CHECK(qf_open(empty,&a)==QF_OK);
    data=NULL;
    length=-1;
    CHECK(qf_read(a,&data,&length)==QF_EOF);
    CHECK(data==NULL && length==-1);
    CHECK(qf_close(a)==QF_OK);

    short refs[QF_SLOTS];

    for(unsigned i=0;i<QF_SLOTS;++i)
        CHECK(qf_open(file,&refs[i])==QF_OK);

    a=-1;

    CHECK(qf_open(file,&a)==QF_LIMIT);
    CHECK(a==-1);

    for(unsigned i=0;i<QF_SLOTS;++i)
        CHECK(qf_close(refs[i])==QF_OK);

    for(unsigned i=0;i<256;++i) {
        CHECK(qf_open(file,&a)==QF_OK);
        CHECK(qf_read(a,&data,&length)==QF_OK);
        CHECK(length==8);
        CHECK(memcmp(data,"D4RLQT16",8)==0);
        free(data);
        CHECK(qf_close(a)==QF_OK);
    }

    /* An open file remains readable after unlink. */
    CHECK(qf_open(file,&a)==QF_OK);
    CHECK(unlink(file)==0);
    CHECK(qf_read(a,&data,&length)==QF_OK);
    CHECK(length==8);
    CHECK(memcmp(data,"D4RLQT16",8)==0);
    free(data);
    CHECK(qf_close(a)==QF_OK);

    printf("FILE_BACKEND_PASS bits=%u checks=%u\n",
        (unsigned)(sizeof(void*)*8),checks);

    return 0;
}
