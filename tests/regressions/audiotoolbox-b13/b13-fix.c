/* SPDX-License-Identifier: GPL-3.0-or-later
 * B13 fixes: before/after tests of ATB-FIX1 and ATB-FIX2 on the production AudioToolbox
 * (or a private candidate laid over it). Mach-O i386 and x86_64; built as C++.
 *
 *   b13-fix fix1 MEDIA_DIR OUT_DIR
 *     mu-law packets read by AudioFileReadPackets, decoded by AudioConverterNew
 *     (ulaw -> S16LE) + AudioConverterFillComplexBuffer, without and with
 *     kAudioConverterDecompressionMagicCookie (decoder recreated); outputs saved.
 *   b13-fix fix2 MEDIA_DIR OUT_DIR
 *     AudioConverterConvertBuffer / AudioConverterConvertComplexBuffer (v2, all or
 *     nothing): argument checks, several buffers with different capacities, output
 *     too small (refused, canaries intact), S16LE->S16BE and S16LE->Float32 over the
 *     whole file with one converter in fixed and varying call sizes, sample rate
 *     conversion refused.
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

/* Canary helpers: 0xA5 everywhere, then checks that a range was left alone. */
static void fill_canary(uint8_t *p, size_t n) { memset(p, 0xA5, n); }
static bool canary_from(const uint8_t *p, size_t from, size_t to)
{
    for (size_t i = from; i < to; ++i)
        if (p[i] != 0xA5)
            return false;
    return true;
}
/* Independent oracle for S16LE -> S16BE: a byte swap. */
static bool is_swapped(const uint8_t *out, const uint8_t *in, size_t bytes)
{
    for (size_t i = 0; i + 1 < bytes; i += 2)
        if (out[i] != in[i + 1] || out[i + 1] != in[i])
            return false;
    return true;
}
static OSStatus complex1(AudioConverterRef c, UInt32 frames, const void *in, UInt32 in_bytes, void *out, UInt32 *out_bytes)
{
    AudioBufferList i, o;
    i.mNumberBuffers = o.mNumberBuffers = 1;
    i.mBuffers[0].mNumberChannels = o.mBuffers[0].mNumberChannels = 2;
    i.mBuffers[0].mData = (void *)in;
    i.mBuffers[0].mDataByteSize = in_bytes;
    o.mBuffers[0].mData = out;
    o.mBuffers[0].mDataByteSize = *out_bytes;
    OSStatus st = AudioConverterConvertComplexBuffer(c, frames, &i, &o);
    *out_bytes = o.mBuffers[0].mDataByteSize;
    return st;
}

/* Contract checked (v2, fixed before the runs): ConvertBuffer/ConvertComplexBuffer convert
 * all of the input or nothing. Output capacity too small -> kAudioConverterErr_InvalidOutputSize,
 * nothing written, size 0; several buffers -> kAudio_ParamError; sample rate conversion ->
 * kAudioConverterErr_FormatNotSupported (the public header: these calls fail for any
 * conversion with a variable input/output size relationship). */
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
    const size_t O = 4096 * 8 + 64;
    uint8_t *o = (uint8_t *)malloc(O), *o2 = (uint8_t *)malloc(O);
    UInt32 osz;
    bool ok;

    /* 1. arguments: nothing converted, nothing written */
    enter("null_converter");
    fill_canary(o, O);
    osz = 16;
    st = AudioConverterConvertBuffer(NULL, 16, s16, &osz, o);
    snprintf(d, sizeof d, "status=%d", (int)st);
    check(st == kAudio_ParamError && canary_from(o, 0, O), "null_converter", d);
    enter("null_output_size");
    st = AudioConverterConvertBuffer(c, 16, s16, NULL, o);
    snprintf(d, sizeof d, "status=%d", (int)st);
    check(st == kAudio_ParamError && canary_from(o, 0, O), "null_output_size", d);
    enter("null_input_nonzero_size");
    osz = 16;
    st = AudioConverterConvertBuffer(c, 16, NULL, &osz, o);
    snprintf(d, sizeof d, "status=%d", (int)st);
    check(st == kAudio_ParamError && canary_from(o, 0, O), "null_input_nonzero_size", d);
    enter("null_output_nonzero_size");
    osz = 16;
    st = AudioConverterConvertBuffer(c, 16, s16, &osz, NULL);
    snprintf(d, sizeof d, "status=%d", (int)st);
    check(st == kAudio_ParamError, "null_output_nonzero_size", d);
    enter("input_not_whole_frames");
    osz = 4096 * 4;
    st = AudioConverterConvertBuffer(c, 4096 * 4 + 2, s16, &osz, o);
    snprintf(d, sizeof d, "status=%d out_untouched=%d", (int)st, canary_from(o, 0, O));
    check(st == kAudioConverterErr_InvalidInputSize && canary_from(o, 0, O), "input_not_whole_frames", d);
    enter("zero_input");
    osz = 4096 * 4;
    st = AudioConverterConvertBuffer(c, 0, s16, &osz, o);
    snprintf(d, sizeof d, "status=%d out_bytes=%u", (int)st, (unsigned)osz);
    check(st == noErr && osz == 0 && canary_from(o, 0, O), "zero_input", d);
    enter("zero_input_null_pointers");
    osz = 0;
    st = AudioConverterConvertBuffer(c, 0, NULL, &osz, NULL);
    snprintf(d, sizeof d, "status=%d out_bytes=%u", (int)st, (unsigned)osz);
    check(st == noErr && osz == 0, "zero_input_null_pointers", d);
    enter("complex_null_lists");
    {
        AudioBufferList l;
        l.mNumberBuffers = 1;
        l.mBuffers[0].mNumberChannels = 2;
        l.mBuffers[0].mData = o;
        l.mBuffers[0].mDataByteSize = 4096;
        OSStatus a = AudioConverterConvertComplexBuffer(c, 16, NULL, &l);
        OSStatus b = AudioConverterConvertComplexBuffer(c, 16, &l, NULL);
        snprintf(d, sizeof d, "status_in=%d status_out=%d", (int)a, (int)b);
        check(a == kAudio_ParamError && b == kAudio_ParamError && canary_from(o, 0, O), "complex_null_lists", d);
    }
    enter("complex_input_short");
    osz = 4096 * 4;
    st = complex1(c, 1000, s16, 1000 * 4 - 1, o, &osz);
    snprintf(d, sizeof d, "status=%d", (int)st);
    check(st == kAudioConverterErr_InvalidInputSize && canary_from(o, 0, O), "complex_input_short", d);

    /* 2. several buffers (a non-interleaved layout), with different capacities: refused, no write */
    enter("complex_two_output_buffers_unequal");
    {
        AudioBufferList *ob = (AudioBufferList *)calloc(1, sizeof(AudioBufferList) + sizeof(AudioBuffer));
        AudioBufferList in;
        fill_canary(o, O);
        fill_canary(o2, O);
        in.mNumberBuffers = 1;
        in.mBuffers[0].mNumberChannels = 2;
        in.mBuffers[0].mData = s16;
        in.mBuffers[0].mDataByteSize = 1000 * 4;
        ob->mNumberBuffers = 2;
        ob->mBuffers[0].mNumberChannels = ob->mBuffers[1].mNumberChannels = 1;
        ob->mBuffers[0].mData = o;
        ob->mBuffers[0].mDataByteSize = 4096 * 4;
        ob->mBuffers[1].mData = o2;
        ob->mBuffers[1].mDataByteSize = 100;
        st = AudioConverterConvertComplexBuffer(c, 1000, &in, ob);
        ok = canary_from(o, 0, O) && canary_from(o2, 0, O);
        snprintf(d, sizeof d, "status=%d untouched=%d", (int)st, ok);
        check(st == kAudio_ParamError && ok, "complex_two_output_buffers_unequal", d);
        free(ob);
    }
    enter("complex_two_input_buffers");
    {
        AudioBufferList *ib = (AudioBufferList *)calloc(1, sizeof(AudioBufferList) + sizeof(AudioBuffer));
        AudioBufferList ob;
        ib->mNumberBuffers = 2;
        ib->mBuffers[0].mNumberChannels = ib->mBuffers[1].mNumberChannels = 1;
        ib->mBuffers[0].mData = s16;
        ib->mBuffers[0].mDataByteSize = 1000 * 2;
        ib->mBuffers[1].mData = s16 + 4096;
        ib->mBuffers[1].mDataByteSize = 1000 * 2;
        ob.mNumberBuffers = 1;
        ob.mBuffers[0].mNumberChannels = 2;
        ob.mBuffers[0].mData = o;
        ob.mBuffers[0].mDataByteSize = 4096 * 4;
        st = AudioConverterConvertComplexBuffer(c, 1000, ib, &ob);
        snprintf(d, sizeof d, "status=%d untouched=%d", (int)st, canary_from(o, 0, O));
        check(st == kAudio_ParamError && canary_from(o, 0, O), "complex_two_input_buffers", d);
        free(ib);
    }

    /* 3. one 4 096-frame buffer, checked here against a byte swap */
    enter("convertbuffer_s16be_4096");
    fill_canary(o, O);
    osz = 4096 * 4;
    st = AudioConverterConvertBuffer(c, 4096 * 4, s16, &osz, o);
    ok = osz == 4096 * 4 && is_swapped(o, s16, 4096 * 4) && canary_from(o, 4096 * 4, O);
    snprintf(d, sizeof d, "status=%d out_bytes=%u exact_and_canary=%d", (int)st, (unsigned)osz, ok);
    check(st == noErr && ok, "convertbuffer_s16be_4096", d);
    enter("complex_input_larger_than_frames");
    fill_canary(o, O);
    osz = 4096 * 4;
    st = complex1(c, 1000, s16, 4096 * 4, o, &osz);
    ok = osz == 1000 * 4 && is_swapped(o, s16, 1000 * 4) && canary_from(o, 1000 * 4, O);
    snprintf(d, sizeof d, "status=%d out_bytes=%u exact_and_canary=%d", (int)st, (unsigned)osz, ok);
    check(st == noErr && ok, "complex_input_larger_than_frames", d);

    /* 4. output smaller than the input needs: refused, nothing written, size 0 */
    enter("capacity_half");
    fill_canary(o, O);
    osz = 2048 * 4;
    st = AudioConverterConvertBuffer(c, 4096 * 4, s16, &osz, o);
    snprintf(d, sizeof d, "status=%d out_bytes=%u untouched=%d", (int)st, (unsigned)osz, canary_from(o, 0, O));
    check(st == kAudioConverterErr_InvalidOutputSize && osz == 0 && canary_from(o, 0, O), "capacity_half", d);
    enter("capacity_one_byte_short");
    osz = 4096 * 4 - 1;
    st = AudioConverterConvertBuffer(c, 4096 * 4, s16, &osz, o);
    snprintf(d, sizeof d, "status=%d out_bytes=%u untouched=%d", (int)st, (unsigned)osz, canary_from(o, 0, O));
    check(st == kAudioConverterErr_InvalidOutputSize && osz == 0 && canary_from(o, 0, O), "capacity_one_byte_short", d);
    enter("complex_output_short");
    osz = 999 * 4;
    st = complex1(c, 1000, s16, 1000 * 4, o, &osz);
    snprintf(d, sizeof d, "status=%d out_bytes=%u untouched=%d", (int)st, (unsigned)osz, canary_from(o, 0, O));
    check(st == kAudioConverterErr_InvalidOutputSize && osz == 0 && canary_from(o, 0, O), "complex_output_short", d);
    enter("after_rejections_next_call_clean");
    osz = 4096 * 4;
    st = AudioConverterConvertBuffer(c, 4096 * 4, s16 + 4096 * 4, &osz, o);
    ok = osz == 4096 * 4 && is_swapped(o, s16 + 4096 * 4, 4096 * 4) && canary_from(o, 4096 * 4, O);
    snprintf(d, sizeof d, "status=%d out_bytes=%u frames_4096_8191_exact=%d", (int)st, (unsigned)osz, ok);
    check(st == noErr && ok, "after_rejections_next_call_clean", d);

    /* 5. the whole file through the same converter: 4 096-frame calls, then varying sizes */
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
    enter("complexbuffer_varchunks_whole_file");
    {
        static const UInt32 sizes[] = { 1, 7, 333, 4096, 1000, 2, 4095, 64 };
        memset(all, 0, n);
        done = 0;
        calls = 0;
        last = noErr;
        bool sizes_ok = true;
        while (done < n) {
            UInt32 frames = sizes[calls % 8];
            if (frames > (n - done) / 4)
                frames = (UInt32)((n - done) / 4);
            osz = frames * 4 + 64; /* larger than needed: the size reported must be exact */
            uint8_t *dst = (uint8_t *)malloc(osz);
            fill_canary(dst, osz);
            last = complex1(c, frames, s16 + done, frames * 4, dst, &osz);
            ++calls;
            sizes_ok &= osz == frames * 4 && canary_from(dst, frames * 4, frames * 4 + 64);
            memcpy(all + done, dst, frames * 4);
            free(dst);
            if (last != noErr || !sizes_ok)
                break;
            done += frames * 4;
        }
        snprintf(d, sizeof d, "status=%d calls=%u bytes=%zu sizes_and_canaries=%d", (int)last, calls, done, sizes_ok);
        check(last == noErr && sizes_ok && done == n && save(out, "fix2-complexbuffer-s16be-varchunks.raw", all, done),
              "complexbuffer_varchunks_whole_file", d);
    }
    AudioConverterDispose(c);

    /* 6. sample rate conversion: a variable relationship, refused by both calls */
    enter("sample_rate_conversion_refused");
    {
        AudioStreamBasicDescription le48 = le;
        le48.mSampleRate = 48000;
        c = NULL;
        OSStatus nw = AudioConverterNew(&le, &le48, &c);
        fill_canary(o, O);
        osz = 4096 * 8;
        OSStatus a = c ? AudioConverterConvertBuffer(c, 4096 * 4, s16, &osz, o) : nw;
        UInt32 osz2 = 4096 * 8;
        OSStatus b = c ? complex1(c, 4096, s16, 4096 * 4, o, &osz2) : nw;
        snprintf(d, sizeof d, "new=%d convertbuffer=%d complex=%d out_bytes=%u untouched=%d", (int)nw, (int)a, (int)b,
                 (unsigned)osz, canary_from(o, 0, O));
        check(nw == noErr && a == kAudioConverterErr_FormatNotSupported && b == kAudioConverterErr_FormatNotSupported
                  && osz == 4096 * 8 && canary_from(o, 0, O), "sample_rate_conversion_refused", d);
        if (c)
            AudioConverterDispose(c);
    }

    /* 7. S16LE -> Float32 through ConvertBuffer (exact: s/32768), 4 096 frames then varying sizes */
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
    enter("convertbuffer_f32_varchunks");
    {
        static const UInt32 sizes[] = { 3, 4096, 17, 1024, 1 };
        memset(f32, 0, n * 2);
        done = 0;
        calls = 0;
        last = st;
        while (st == noErr && done < n) {
            UInt32 frames = sizes[calls % 5];
            if (frames > (n - done) / 4)
                frames = (UInt32)((n - done) / 4);
            osz = frames * 8 + 32;
            last = AudioConverterConvertBuffer(c, frames * 4, s16 + done, &osz, f32 + done * 2);
            ++calls;
            if (last != noErr || osz != frames * 8)
                break;
            done += frames * 4;
        }
        snprintf(d, sizeof d, "status=%d calls=%u bytes_in=%zu", (int)last, calls, done);
        check(st == noErr && last == noErr && done == n && save(out, "fix2-convertbuffer-f32-varchunks.raw", f32, n * 2),
              "convertbuffer_f32_varchunks", d);
    }
    if (c)
        AudioConverterDispose(c);
    free(all);
    free(f32);
    free(o);
    free(o2);
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
