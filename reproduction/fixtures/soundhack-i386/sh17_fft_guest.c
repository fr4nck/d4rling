extern void InitFFTTable(void);
extern void FFT(float *, long, short);
extern void RealFFT(float *, long, short);
extern float gOmegaPiReal[31], gOmegaPiImag[31];
extern long write(int, const void *, unsigned long);

struct sample {
    volatile float before;
    float a[16];
    volatile float after;
};

static int closef(float x, float y, float eps) {
    float d = x-y;
    return (d < 0 ? -d : d) <= eps;
}

static int guards(const struct sample *s) {
    return s->before == 7331.0f && s->after == -9773.0f;
}

static void line(const char *s) {
    unsigned long n=0;
    while(s[n]) n++;
    (void)write(1,s,n);
    (void)write(1,"\n",1);
}

int main(void) {
    int j;
    struct sample x = {7331.0f,{0.0f},-9773.0f};

    InitFFTTable();

    if (!closef(gOmegaPiReal[1],-1.0f,.0005f) ||
        !closef(gOmegaPiImag[1],1.0f,.0005f) ||
        !closef(gOmegaPiImag[2],.70710678f,.0005f))
        return 21;

    line("SOUNDHACK_SH17_INIT_PASS");

    x.a[0]=1.0f;
    x.a[8]=1.0f;

    FFT(x.a,8L,1);

    if (!guards(&x)) return 22;

    for(j=0;j<8;j++)
        if (!closef(x.a[2*j],(j%2==0)?2.0f:0.0f,.001f) ||
            !closef(x.a[2*j+1],0.0f,.001f))
            return 23;

    FFT(x.a,8L,0);

    if (!guards(&x)) return 24;

    for(j=0;j<16;j++)
        if (!closef(x.a[j],(j==0||j==8)?1.0f:0.0f,.001f))
            return 25;

    line("SOUNDHACK_SH17_COMPLEX_FFT_PASS");

    for(j=0;j<16;j++) x.a[j]=0.0f;
    x.a[0]=1.0f;

    RealFFT(x.a,8L,1);

    if (!guards(&x) ||
        !closef(x.a[0],1.0f,.001f) ||
        !closef(x.a[1],1.0f,.001f))
        return 26;

    for(j=1;j<8;j++)
        if (!closef(x.a[2*j],1.0f,.001f) ||
            !closef(x.a[2*j+1],0.0f,.001f))
            return 27;

    RealFFT(x.a,8L,0);

    if (!guards(&x)) return 28;

    for(j=0;j<16;j++)
        if (!closef(x.a[j],j==0?1.0f:0.0f,.001f))
            return 29;

    line("SOUNDHACK_SH17_REAL_IMPULSE_PASS");
    line("SOUNDHACK_SH17_GUEST_FFT_PASS");
    return 0;
}
