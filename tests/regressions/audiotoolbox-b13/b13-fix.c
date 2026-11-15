/* SPDX-License-Identifier: GPL-3.0-or-later
 * B13 fixes: before/after tests of ATB-FIX1 and ATB-FIX2 on the production AudioToolbox
 * (or a private candidate laid over it). Mach-O i386 and x86_64; built as C++.
 *
 *   b13-fix fix1 MEDIA_DIR OUT_DIR
 *     mu-law packets read by AudioFileReadPackets, decoded by AudioConverterNew
 *     (ulaw -> S16LE) + AudioConverterFillComplexBuffer, without and with
 *     kAudioConverterDecompressionMagicCookie (decoder recreated); outputs saved.
 *   b13-fix fix2 MEDIA_DIR OUT_DIR
 *     AudioConverterConvertBuffer / AudioConverterConvertComplexBuffer: argument
 *     checks first, then S16LE->S16BE and S16LE->Float32 conversions, reuse of one
 *     converter over the whole file, capacity limits with canaries.
 * Expected results are fixed here before the runs; outputs are also compared
 * outside the guest with b13-oracle.json (verify_b13_fix.py).
 */
#include <AudioToolbox/AudioToolbox.h>
#include <CoreFoundation/CoreFoundation.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static unsigned checks, failures;
static void check(bool ok, const char *name, const char *detail)
{
    ++checks;
    if (!ok)
        ++failures;
    printf("B13FIX %s %s %s\n", name, ok ? "PASS" : "FAIL", detail);
    fflush(stdout);
}
static void enter(const char *name)
{
    printf("B13FIX_ENTER %s\n", name);
    fflush(stdout);
}

static bool save(const char *dir, const char *name, const void *p, size_t n)
{
    char path[4096];
    snprintf(path, sizeof path, "%s/%s", dir, name);
    FILE *f = fopen(path, "wb");
    bool ok = f && fwrite(p, 1, n, f) == n;
    if (f && fclose(f) != 0)
        ok = false;
    return ok;
}

static AudioStreamBasicDescription pcm(UInt32 bits, bool flt, bool big)
{
    AudioStreamBasicDescription f = {};
    f.mSampleRate = 44100;
    f.mFormatID = kAudioFormatLinearPCM;
    f.mFormatFlags = (flt ? kAudioFormatFlagIsFloat : kAudioFormatFlagIsSignedInteger) | kAudioFormatFlagIsPacked
                     | (big ? kAudioFormatFlagIsBigEndian : 0);
    f.mChannelsPerFrame = 2;
    f.mBitsPerChannel = bits;
    f.mFramesPerPacket = 1;
    f.mBytesPerFrame = f.mBytesPerPacket = bits / 8 * 2;
    return f;
}

/* Packets of a file, through AudioFile (the same route as the B13 probe). */
static uint8_t *read_packets(const char *media, const char *name, size_t *n, AudioStreamBasicDescription *fmt)
{
    char path[4096];
    snprintf(path, sizeof path, "%s/%s", media, name);
    CFURLRef u = CFURLCreateFromFileSystemRepresentation(NULL, (const UInt8 *)path, (CFIndex)strlen(path), false);
    AudioFileID af = NULL;
    OSStatus st = AudioFileOpenURL(u, kAudioFileReadPermission, 0, &af);
    CFRelease(u);
    if (st != noErr)
        return NULL;
    UInt32 sz = sizeof *fmt;
    AudioFileGetProperty(af, kAudioFilePropertyDataFormat, &sz, fmt);
    size_t cap = 88200 * 4 + 65536, got = 0;
    uint8_t *buf = (uint8_t *)malloc(cap);
    SInt64 at = 0;
    for (int i = 0; i < 1000; ++i) {
        UInt32 k = 4096, nb = 4096 * 4;
        st = AudioFileReadPackets(af, false, &nb, NULL, at, &k, buf + got);
        if ((st != noErr && st != kAudioFileEndOfFileError) || k == 0)
            break;
        got += nb;
        at += k;
    }
    AudioFileClose(af);
    *n = got;
    return buf;
}

struct feed { const uint8_t *p; size_t n, pos; UInt32 bpf; };
static OSStatus feed_proc(AudioConverterRef, UInt32 *io, AudioBufferList *bl, AudioStreamPacketDescription **pd, void *u)
{
    struct feed *f = (struct feed *)u;
    size_t avail = (f->n - f->pos) / f->bpf;
    UInt32 k = *io < avail ? *io : (UInt32)avail;
    if (pd)
        *pd = NULL;
    bl->mNumberBuffers = 1;
    bl->mBuffers[0].mNumberChannels = 2;
    bl->mBuffers[0].mData = (void *)(f->p + f->pos);
    bl->mBuffers[0].mDataByteSize = k * f->bpf;
    f->pos += (size_t)k * f->bpf;
    *io = k;
    return noErr;
}

static int fix1(const char *media, const char *out)
{
    char d[512];
    size_t n = 0;
    AudioStreamBasicDescription in = {};
    uint8_t *ulaw = read_packets(media, "demo-ulaw.wav", &n, &in);
    snprintf(d, sizeof d, "bytes=%zu format=%08x channels=%u rate=%.0f", n, (unsigned)in.mFormatID, (unsigned)in.mChannelsPerFrame,
             in.mSampleRate);
    check(ulaw && n == 88200 * 2 && in.mFormatID == kAudioFormatULaw, "read_ulaw_packets", d);
    if (!ulaw)
        return 3;
    AudioStreamBasicDescription o = pcm(16, false, false);
    for (int cookie = 0; cookie < 2; ++cookie) {
        const char *tag = cookie ? "ulaw_s16_after_cookie" : "ulaw_s16";
        AudioConverterRef c = NULL;
        OSStatus st = AudioConverterNew(&in, &o, &c);
        char name[96];
        snprintf(name, sizeof name, "converter_new[%s]", tag);
        snprintf(d, sizeof d, "status=%d", (int)st);
        check(st == noErr && c, name, d);
        if (st != noErr)
            continue;
        if (cookie) {
            /* G.711 has no cookie: any bytes make the converter recreate its decoder */
            static const uint8_t blob[8] = { 0, 1, 2, 3, 4, 5, 6, 7 };
            st = AudioConverterSetProperty(c, kAudioConverterDecompressionMagicCookie, sizeof blob, blob);
            snprintf(name, sizeof name, "set_cookie[%s]", tag);
            snprintf(d, sizeof d, "status=%d", (int)st);
            check(st == noErr, name, d);
        }
        size_t cap = 88200 * 4 + 65536, got = 0;
        uint8_t *buf = (uint8_t *)malloc(cap);
        struct feed f = { ulaw, n, 0, 2 };
        OSStatus rs = noErr;
        for (int i = 0; i < 1000; ++i) {
            UInt32 k = 4096;
            AudioBufferList bl;
            bl.mNumberBuffers = 1;
            bl.mBuffers[0].mNumberChannels = 2;
            bl.mBuffers[0].mDataByteSize = k * 4;
            bl.mBuffers[0].mData = buf + got;
            rs = AudioConverterFillComplexBuffer(c, feed_proc, &f, &k, &bl, NULL);
            if (rs != noErr || k == 0)
                break;
            got += (size_t)k * 4;
        }
        snprintf(name, sizeof name, "convert[%s]", tag);
        snprintf(d, sizeof d, "status=%d frames=%zu", (int)rs, got / 4);
        char file[96];
        snprintf(file, sizeof file, "fix1-%s.s16le", tag);
        check(rs == noErr && got == 88200 * 4 && save(out, file, buf, got), name, d);
        free(buf);
        AudioConverterDispose(c);
    }
    printf("B13FIX_SUMMARY checks=%u failures=%u\n", checks, failures);
    return failures ? 1 : 0;
}

static int fix2(const char *media, const char *out)
{
    char d[512];
    size_t n = 0;
    AudioStreamBasicDescription f = {};
    uint8_t *s16 = read_packets(media, "demo-s16.wav", &n, &f);
    check(s16 && n == 88200 * 4, "read_s16le_packets", "");
    if (!s16)
        return 3;
    AudioStreamBasicDescription le = pcm(16, false, false), be = pcm(16, false, true), fl = pcm(32, true, false);
    AudioConverterRef c = NULL;
    OSStatus st = AudioConverterNew(&le, &be, &c);
    check(st == noErr && c, "converter_new[s16le->s16be]", "");
    if (st != noErr)
        return 4;

    /* 1. argument checks (nothing is converted, nothing is written) */
    enter("null_converter");
    UInt32 osz = 16;
    uint8_t tiny[16];
    st = AudioConverterConvertBuffer(NULL, 16, s16, &osz, tiny);
    snprintf(d, sizeof d, "status=%d", (int)st);
    check(st == kAudio_ParamError, "null_converter", d);
    enter("null_output_size");
    st = AudioConverterConvertBuffer(c, 16, s16, NULL, tiny);
    snprintf(d, sizeof d, "status=%d", (int)st);
    check(st == kAudio_ParamError, "null_output_size", d);
    enter("input_not_whole_frames");
    uint8_t *o = (uint8_t *)malloc(4096 * 8 + 64);
    memset(o, 0xA5, 4096 * 8 + 64);
    osz = 4096 * 4;
    st = AudioConverterConvertBuffer(c, 4096 * 4 + 2, s16, &osz, o);
    bool untouched = true;
    for (int i = 0; i < 4096 * 8 + 64; ++i)
        untouched &= o[i] == 0xA5;
    snprintf(d, sizeof d, "status=%d out_untouched=%d", (int)st, untouched);
    check(st == kAudioConverterErr_InvalidInputSize && untouched, "input_not_whole_frames", d);
    enter("zero_input");
    osz = 4096 * 4;
    st = AudioConverterConvertBuffer(c, 0, s16, &osz, o);
    snprintf(d, sizeof d, "status=%d out_bytes=%u", (int)st, (unsigned)osz);
    check(st == noErr && osz == 0, "zero_input", d);
    enter("complex_input_size_mismatch");
    {
        AudioBufferList in, ob;
        in.mNumberBuffers = ob.mNumberBuffers = 1;
        in.mBuffers[0].mNumberChannels = ob.mBuffers[0].mNumberChannels = 2;
        in.mBuffers[0].mData = s16;
        in.mBuffers[0].mDataByteSize = 1000 * 4 + 1;
        ob.mBuffers[0].mData = o;
        ob.mBuffers[0].mDataByteSize = 1000 * 4;
        st = AudioConverterConvertComplexBuffer(c, 1000, &in, &ob);
        snprintf(d, sizeof d, "status=%d", (int)st);
        check(st == kAudioConverterErr_InvalidInputSize, "complex_input_size_mismatch", d);
    }

    /* 2. a 4 096-frame buffer, S16LE -> S16BE, checked here byte by byte */
    enter("convertbuffer_s16be_4096");
    memset(o, 0xA5, 4096 * 8 + 64);
    osz = 4096 * 4;
    st = AudioConverterConvertBuffer(c, 4096 * 4, s16, &osz, o);
    bool same = osz == 4096 * 4;
    for (UInt32 i = 0; same && i < 4096 * 2; ++i)
        same = o[2 * i] == s16[2 * i + 1] && o[2 * i + 1] == s16[2 * i];
    bool canary = true;
    for (int i = 4096 * 4; i < 4096 * 8 + 64; ++i)
        canary &= o[i] == 0xA5;
    snprintf(d, sizeof d, "status=%d out_bytes=%u swapped=%d canary=%d", (int)st, (unsigned)osz, same, canary);
    check(st == noErr && same && canary, "convertbuffer_s16be_4096", d);

    /* 3. the whole file through the same converter, 4 096 frames per call */
    enter("convertbuffer_whole_file_reuse");
    uint8_t *all = (uint8_t *)malloc(n);
    size_t done = 0;
    unsigned calls = 0;
    OSStatus last = noErr;
    while (done < n) {
        UInt32 in_bytes = (UInt32)(n - done < 4096 * 4 ? n - done : 4096 * 4);
        osz = in_bytes;
        last = AudioConverterConvertBuffer(c, in_bytes, s16 + done, &osz, all + done);
        ++calls;
        if (last != noErr || osz != in_bytes)
            break;
        done += in_bytes;
    }
    snprintf(d, sizeof d, "status=%d calls=%u bytes=%zu", (int)last, calls, done);
    check(last == noErr && done == n && save(out, "fix2-convertbuffer-s16be.raw", all, done), "convertbuffer_whole_file_reuse", d);

    /* 4. capacity smaller than the input: whole frames that fit, nothing beyond */
    enter("capacity_half");
    memset(o, 0xA5, 4096 * 8 + 64);
    osz = 2048 * 4;
    st = AudioConverterConvertBuffer(c, 4096 * 4, s16, &osz, o);
    same = osz == 2048 * 4 && !memcmp(o, all, 2048 * 4);
    canary = true;
    for (int i = 2048 * 4; i < 4096 * 8 + 64; ++i)
        canary &= o[i] == 0xA5;
    snprintf(d, sizeof d, "status=%d out_bytes=%u prefix_ok=%d canary=%d", (int)st, (unsigned)osz, same, canary);
    check(st == noErr && same && canary, "capacity_half", d);
    enter("capacity_not_whole_frames");
    memset(o, 0xA5, 4096 * 8 + 64);
    osz = 4096 * 4 - 1;
    st = AudioConverterConvertBuffer(c, 4096 * 4, s16, &osz, o);
    same = osz == 4095 * 4 && !memcmp(o, all, 4095 * 4);
    canary = true;
    for (int i = 4095 * 4; i < 4096 * 8 + 64; ++i)
        canary &= o[i] == 0xA5;
    snprintf(d, sizeof d, "status=%d out_bytes=%u prefix_ok=%d canary=%d", (int)st, (unsigned)osz, same, canary);
    check(st == noErr && same && canary, "capacity_not_whole_frames", d);
    enter("after_partial_next_call_clean");
    osz = 4096 * 4;
    st = AudioConverterConvertBuffer(c, 4096 * 4, s16 + 4096 * 4, &osz, o);
    same = osz == 4096 * 4 && !memcmp(o, all + 4096 * 4, 4096 * 4);
    snprintf(d, sizeof d, "status=%d out_bytes=%u matches_frames_4096_8191=%d", (int)st, (unsigned)osz, same);
    check(st == noErr && same, "after_partial_next_call_clean", d);
    AudioConverterDispose(c);

    /* 5. S16LE -> Float32 through ConvertBuffer (exact: s/32768) */
    enter("convertbuffer_f32_whole_file");
    c = NULL;
    st = AudioConverterNew(&le, &fl, &c);
    uint8_t *f32 = (uint8_t *)malloc(n * 2);
    done = 0;
    last = st;
    while (st == noErr && done < n) {
        UInt32 in_bytes = (UInt32)(n - done < 4096 * 4 ? n - done : 4096 * 4);
        osz = in_bytes * 2;
        last = AudioConverterConvertBuffer(c, in_bytes, s16 + done, &osz, f32 + done * 2);
        if (last != noErr || osz != in_bytes * 2)
            break;
        done += in_bytes;
    }
    snprintf(d, sizeof d, "new=%d status=%d bytes_in=%zu", (int)st, (int)last, done);
    check(st == noErr && last == noErr && done == n && save(out, "fix2-convertbuffer-f32.raw", f32, n * 2),
          "convertbuffer_f32_whole_file", d);
    if (c)
        AudioConverterDispose(c);
    free(all);
    free(f32);
    free(o);
    printf("B13FIX_SUMMARY checks=%u failures=%u\n", checks, failures);
    return failures ? 1 : 0;
}

int main(int argc, char **argv)
{
    printf("B13FIX_ABI pointer_bits=%zu\n", sizeof(void *) * 8);
    fflush(stdout);
    if (argc == 4 && !strcmp(argv[1], "fix1"))
        return fix1(argv[2], argv[3]);
    if (argc == 4 && !strcmp(argv[1], "fix2"))
        return fix2(argv[2], argv[3]);
    fprintf(stderr, "usage: b13-fix fix1|fix2 MEDIA OUT\n");
    return 2;
}
