
typedef signed short SInt16;
typedef signed int SInt32;
typedef void *Movie;

typedef struct {
    const char *dli_fname;
    void *dli_fbase;
    const char *dli_sname;
    void *dli_saddr;
} Dl_info;

extern void *dlopen(const char *,int);
extern void *dlsym(void *,const char *);
extern int dlclose(void *);
extern char *dlerror(void);
extern int dladdr(const void *,Dl_info *);

extern int printf(const char *,...);
extern int fflush(void *);
extern int strcmp(const char *,const char *);
extern char *realpath(const char *,char *);

static unsigned checks;
static unsigned failures;

static void check(int ok,const char *name)
{
    ++checks;

    if (!ok)
        ++failures;

    printf("%s %s\n",ok?"PASS":"FAIL",name);
    fflush(0);
}

static void *resolve(
    void *library,const char *name,const char *expected
)
{
    void *p=dlsym(library,name);
    Dl_info info={0};
    char actual[4096];
    char wanted[4096];

    if (!p) {
        printf("SYMBOL_MISSING %s\n",name);
        fflush(0);
        return 0;
    }

    if (!dladdr(p,&info) || !info.dli_fname) {
        printf("PROVIDER_UNKNOWN %s\n",name);
        fflush(0);
        return 0;
    }

    printf("PROVIDER %s %s\n",name,info.dli_fname);
    fflush(0);

    if (strcmp(info.dli_fname,expected)==0)
        return p;

    if (
        realpath(info.dli_fname,actual)
        && realpath(expected,wanted)
        && strcmp(actual,wanted)==0
    )
        return p;

    printf("PROVIDER_MISMATCH %s\n",name);
    fflush(0);

    return 0;
}

#define LOAD(type,var,name) \
    type var=(type)resolve(lib,name,argv[1]); \
    if (!var) return 21

int main(int argc,char **argv)
{
    printf("WITNESS_START bits=%u\n",
           (unsigned)(sizeof(void*)*8));
    fflush(0);

    if (argc!=2)
        return 20;

    /* Negative control: no fallback to an installed framework. */
    void *bad=dlopen(
        "/__d4rl_qt11_nonexistent__/QuickTime",6
    );

    check(bad==0,"missing framework rejected");

    if (bad) {
        dlclose(bad);
        return 22;
    }

    dlerror();

    /* Darwin RTLD_NOW | RTLD_LOCAL. */
    void *lib=dlopen(argv[1],6);

    if (!lib) {
        const char *e=dlerror();

        printf("LOAD_ERROR %s\n",e?e:"unknown");
        fflush(0);
        return 23;
    }

    printf("CANDIDATE_LOADED %s\n",argv[1]);
    fflush(0);

    typedef SInt16 (*EnterFn)(void);
    typedef void (*ExitFn)(void);
    typedef Movie (*NewFn)(SInt16);
    typedef void (*DisposeFn)(Movie);
    typedef SInt32 (*QueryFn)(Movie);
    typedef void (*ScaleFn)(Movie,SInt32);
    typedef SInt32 (*TimeFn)(Movie,void *);
    typedef void (*SegmentFn)(Movie,SInt32,SInt32);

    LOAD(EnterFn,enter,"EnterMovies");
    LOAD(ExitFn,leave,"ExitMovies");
    LOAD(NewFn,create,"NewMovie");
    LOAD(DisposeFn,dispose,"DisposeMovie");
    LOAD(QueryFn,getScale,"GetMovieTimeScale");
    LOAD(QueryFn,getDuration,"GetMovieDuration");
    LOAD(QueryFn,getTracks,"GetMovieTrackCount");
    LOAD(ScaleFn,setScale,"SetMovieTimeScale");
    LOAD(TimeFn,getTime,"GetMovieTime");
    LOAD(SegmentFn,setSegment,"SetMovieActiveSegment");

    SInt16 rc=enter();

    check(rc==0,"EnterMovies");

    if (rc)
        return 24;

    Movie a=create(0);
    Movie b=create(0);

    check(a!=0,"NewMovie A");
    check(b!=0,"NewMovie B");
    check(a!=b,"independent movie handles");

    if (!a || !b || a==b) {
        if (a) dispose(a);
        if (b && b!=a) dispose(b);
        leave();
        return 25;
    }

    SInt32 bScale=getScale(b);

    check(getScale(a)>0,"initial positive timescale");
    check(bScale>0,"second positive timescale");

    check(getDuration(a)==0,"empty duration A");
    check(getDuration(b)==0,"empty duration B");

    check(getTracks(a)==0,"empty track count A");
    check(getTracks(b)==0,"empty track count B");

    check(getTime(a,0)==0,"initial position A");
    check(getTime(b,0)==0,"initial position B");

    const SInt32 scales[]={1,600,44100,48000,96000};

    for (unsigned i=0;i<5;++i) {
        setScale(a,scales[i]);

        check(
            getScale(a)==scales[i],
            "timescale round trip"
        );

        check(
            getScale(b)==bScale,
            "timescale isolation"
        );

        check(
            getDuration(a)==0,
            "empty duration preserved"
        );
    }

    setSegment(a,0,0);

    check(getTime(a,0)==0,"empty segment position");
    check(getTime(b,0)==0,"segment isolation");

    dispose(a);
    dispose(b);

    for (unsigned i=0;i<128;++i) {
        Movie m=create(0);

        if (!m) {
            check(0,"repeated lifecycle");
            break;
        }

        check(
            getDuration(m)==0
            && getTracks(m)==0
            && getTime(m,0)==0,
            "repeated lifecycle"
        );

        dispose(m);
    }

    leave();

    rc=enter();
    check(rc==0,"re-enter Movies subsystem");

    if (rc==0) {
        Movie m=create(0);
        check(m!=0,"movie creation after re-enter");

        if (m)
            dispose(m);

        leave();
    }

    dlclose(lib);

    printf("CHECKS=%u FAILURES=%u\n",checks,failures);

    if (!failures)
        printf("WITNESS_PASS bits=%u\n",
               (unsigned)(sizeof(void*)*8));

    fflush(0);

    return failures?30:0;
}
