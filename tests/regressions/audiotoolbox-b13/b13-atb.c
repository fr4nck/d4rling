/* SPDX-License-Identifier: GPL-3.0-or-later
 * B13: AudioToolbox witness (Mach-O i386 and x86_64), production frameworks only.
 *
 *   b13-atb probe MEDIA_DIR OUT_DIR
 *     A  images of the tested symbols, loaded native bridges, readable file types
 *     B  AudioFileOpenURL + properties + AudioFileReadPackets/ReadPacketData on
 *        WAV, AIFF, CAF and mu-law WAV; negative files (missing, garbage, empty,
 *        truncated)
 *     C  ExtAudioFileOpenURL + client formats (S16->Float32, mu-law->S16,
 *        44.1->48 kHz Float32, AIFF big-endian->S16LE); AudioConverterNew +
 *        AudioConverterFillComplexBuffer (S16LE->Float32); AudioConverterConvertBuffer
 *     Decoded data are written to OUT_DIR; the oracle comparison is made by
 *     verify_b13.py outside the guest.
 *   b13-atb convertbuffer MEDIA_DIR OUT_DIR
 *     AudioConverterConvertBuffer S16LE->S16BE on 4 096 frames (separate process:
 *     the current implementation is suspected to crash)
 *   b13-atb play MEDIA_DIR OUT_DIR play|stoprestart [FILE]
 *     D  FILE (default demo-s16.aiff, 16-bit big-endian) decoded by ExtAudioFile
 *        through AudioConverter to S16LE before Play, then the CoreAudio IOProc
 *        copies those bytes unchanged (B12 scheme).
 * Built as C++ (Darling's CoreAudio headers). APIs as documented in the public
 * AudioToolbox headers (AudioFile.h, ExtendedAudioFile.h, AudioConverter.h).
 */
#include <AudioToolbox/AudioToolbox.h>
#include <CoreAudio/CoreAudio.h>
#include <CoreFoundation/CoreFoundation.h>
#include <dlfcn.h>
#include <mach-o/dyld.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/time.h>
#include <unistd.h>

static unsigned checks, failures;
static void check(bool ok, const char *name, const char *detail)
{
    ++checks;
    if (!ok)
        ++failures;
    printf("B13 %s %s %s\n", name, ok ? "PASS" : "FAIL", detail);
    fflush(stdout);
}
static void note(const char *name, const char *detail)
{
    printf("B13_OBS %s %s\n", name, detail);
    fflush(stdout);
}

static const char *fourcc(UInt32 v, char *b)
{
    b[0] = (char)(v >> 24); b[1] = (char)(v >> 16); b[2] = (char)(v >> 8); b[3] = (char)v; b[4] = 0;
    for (int i = 0; i < 4; ++i)
        if (b[i] < 32 || b[i] > 126) { snprintf(b, 16, "%d", (int)v); break; }
    return b;
}

static uint64_t fnv(const uint8_t *p, size_t n)
{
    uint64_t h = 0xcbf29ce484222325ULL;
    for (size_t i = 0; i < n; ++i) { h ^= p[i]; h *= 0x100000001b3ULL; }
    return h;
}

static CFURLRef url_for(const char *dir, const char *name)
{
    char path[4096];
    snprintf(path, sizeof path, "%s/%s", dir, name);
    return CFURLCreateFromFileSystemRepresentation(NULL, (const UInt8 *)path, (CFIndex)strlen(path), false);
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

static void image(const char *what, const void *sym)
{
    Dl_info di;
    if (dladdr(sym, &di))
        printf("B13_IMAGE %s %s\n", what, di.dli_fname);
    else
        printf("B13_IMAGE %s ?\n", what);
}

static AudioStreamBasicDescription pcm(double rate, UInt32 bits, bool flt, bool big)
{
    AudioStreamBasicDescription f = {};
    f.mSampleRate = rate;
    f.mFormatID = kAudioFormatLinearPCM;
    f.mFormatFlags = (flt ? kAudioFormatFlagIsFloat : kAudioFormatFlagIsSignedInteger) | kAudioFormatFlagIsPacked
                     | (big ? kAudioFormatFlagIsBigEndian : 0);
    f.mChannelsPerFrame = 2;
    f.mBitsPerChannel = bits;
    f.mFramesPerPacket = 1;
    f.mBytesPerFrame = f.mBytesPerPacket = bits / 8 * 2;
    return f;
}

/* ---- B: AudioFile ----------------------------------------------------------- */
static uint8_t *g_wav_packets; /* demo-s16.wav packets, reused as AudioConverter input */
static size_t g_wav_bytes;

static void audiofile_case(const char *media, const char *out, const char *name, bool keep)
{
    char d[1024], f1[16], f2[16], tag[96];
    CFURLRef u = url_for(media, name);
    AudioFileID af = NULL;
    OSStatus st = AudioFileOpenURL(u, kAudioFileReadPermission, 0, &af);
    CFRelease(u);
    snprintf(tag, sizeof tag, "audiofile_open[%s]", name);
    snprintf(d, sizeof d, "status=%d", (int)st);
    check(st == noErr && af, tag, d);
    if (st != noErr)
        return;
    UInt32 type = 0, sz = sizeof type;
    OSStatus s1 = AudioFileGetProperty(af, kAudioFilePropertyFileFormat, &sz, &type);
    AudioStreamBasicDescription f = {};
    sz = sizeof f;
    OSStatus s2 = AudioFileGetProperty(af, kAudioFilePropertyDataFormat, &sz, &f);
    UInt64 packets = 0, bytes = 0;
    sz = sizeof packets;
    OSStatus s3 = AudioFileGetProperty(af, kAudioFilePropertyAudioDataPacketCount, &sz, &packets);
    sz = sizeof bytes;
    OSStatus s4 = AudioFileGetProperty(af, kAudioFilePropertyAudioDataByteCount, &sz, &bytes);
    UInt32 maxp = 0;
    sz = sizeof maxp;
    OSStatus s5 = AudioFileGetProperty(af, kAudioFilePropertyMaximumPacketSize, &sz, &maxp);
    Float64 dur = 0;
    sz = sizeof dur;
    OSStatus s6 = AudioFileGetProperty(af, kAudioFilePropertyEstimatedDuration, &sz, &dur);
    snprintf(tag, sizeof tag, "audiofile_props[%s]", name);
    snprintf(d, sizeof d,
             "status=%d,%d,%d,%d,%d,%d file_type=%s format=%s flags=0x%x rate=%.1f channels=%u bits=%u "
             "bytes_per_packet=%u frames_per_packet=%u packets=%llu data_bytes=%llu max_packet=%u duration=%.6f",
             (int)s1, (int)s2, (int)s3, (int)s4, (int)s5, (int)s6, fourcc(type, f1), fourcc(f.mFormatID, f2),
             (unsigned)f.mFormatFlags, f.mSampleRate, (unsigned)f.mChannelsPerFrame, (unsigned)f.mBitsPerChannel,
             (unsigned)f.mBytesPerPacket, (unsigned)f.mFramesPerPacket, (unsigned long long)packets,
             (unsigned long long)bytes, (unsigned)maxp, dur);
    printf("B13_PROPS %s %s\n", name, d);
    check(s1 == noErr && s2 == noErr && s3 == noErr && f.mSampleRate == 44100 && f.mChannelsPerFrame == 2, tag, d);

    /* AudioFileReadPackets until it returns no packet */
    size_t cap = (size_t)(packets ? packets : 1) * (f.mBytesPerPacket ? f.mBytesPerPacket : 4) + 65536, got = 0;
    uint8_t *buf = (uint8_t *)malloc(cap);
    SInt64 at = 0;
    unsigned calls = 0;
    OSStatus rs = noErr;
    while (calls < 10000) {
        UInt32 n = 4096, nb = (UInt32)(cap - got < 4096u * 8 ? cap - got : 4096u * 8);
        rs = AudioFileReadPackets(af, false, &nb, NULL, at, &n, buf + got);
        ++calls;
        if (rs != noErr && rs != kAudioFileEndOfFileError)
            break;
        got += nb;
        at += n;
        if (n == 0 || rs == kAudioFileEndOfFileError)
            break;
    }
    snprintf(tag, sizeof tag, "audiofile_readpackets[%s]", name);
    snprintf(d, sizeof d, "last_status=%d calls=%u packets=%lld bytes=%zu fnv64=%016llx", (int)rs, calls, (long long)at, got,
             (unsigned long long)fnv(buf, got));
    printf("B13_READ %s %s\n", name, d);
    char file[256];
    snprintf(file, sizeof file, "%s.packets", name);
    check((rs == noErr || rs == kAudioFileEndOfFileError) && save(out, file, buf, got), tag, d);

    /* AudioFileReadPacketData from packet 1000, 2048 packets */
    UInt32 n2 = 2048, nb2 = 2048 * 8;
    uint8_t *b2 = (uint8_t *)malloc(nb2);
    OSStatus ps = AudioFileReadPacketData(af, false, &nb2, NULL, 1000, &n2, b2);
    snprintf(tag, sizeof tag, "audiofile_readpacketdata[%s]", name);
    snprintf(d, sizeof d, "status=%d packets=%u bytes=%u", (int)ps, (unsigned)n2, (unsigned)nb2);
    snprintf(file, sizeof file, "%s.pd1000", name);
    check(ps == noErr && n2 == 2048 && save(out, file, b2, nb2), tag, d);
    free(b2);
    if (keep) {
        g_wav_packets = buf;
        g_wav_bytes = got;
    } else
        free(buf);
    OSStatus cs = AudioFileClose(af);
    snprintf(tag, sizeof tag, "audiofile_close[%s]", name);
    snprintf(d, sizeof d, "status=%d", (int)cs);
    check(cs == noErr, tag, d);
}

/* Negative files: the outcome is recorded; verify_b13.py applies the criteria. */
static void negative_case(const char *media, const char *out, const char *name)
{
    char d[512], f1[16];
    CFURLRef u = url_for(media, name);
    AudioFileID af = NULL;
    OSStatus st = AudioFileOpenURL(u, kAudioFileReadPermission, 0, &af);
    CFRelease(u);
    if (st != noErr) {
        snprintf(d, sizeof d, "open_status=%d (%s) handle=%s", (int)st, fourcc((UInt32)st, f1), af ? "set" : "null");
        note(name, d);
        return;
    }
    UInt64 packets = 0;
    UInt32 sz = sizeof packets;
    OSStatus s1 = AudioFileGetProperty(af, kAudioFilePropertyAudioDataPacketCount, &sz, &packets);
    uint8_t *buf = (uint8_t *)malloc(1 << 20);
    size_t got = 0;
    SInt64 at = 0;
    OSStatus rs = noErr;
    for (int i = 0; i < 1000; ++i) {
        UInt32 n = 4096, nb = 4096 * 4;
        if (got + nb > (1u << 20))
            break;
        rs = AudioFileReadPackets(af, false, &nb, NULL, at, &n, buf + got);
        if (rs != noErr && rs != kAudioFileEndOfFileError)
            break;
        got += nb;
        at += n;
        if (n == 0 || rs == kAudioFileEndOfFileError)
            break;
    }
    char file[256];
    snprintf(file, sizeof file, "%s.packets", name);
    save(out, file, buf, got);
    free(buf);
    OSStatus cs = AudioFileClose(af);
    snprintf(d, sizeof d, "open_status=0 count_status=%d packets_reported=%llu read_last_status=%d packets_read=%lld bytes_read=%zu close=%d",
             (int)s1, (unsigned long long)packets, (int)rs, (long long)at, got, (int)cs);
    note(name, d);
}

/* ---- C: ExtAudioFile and AudioConverter --------------------------------------- */
static void ext_case(const char *media, const char *out, const char *tagname, const char *name,
                     AudioStreamBasicDescription client, size_t max_frames)
{
    char d[1024], f1[16], tag[96];
    CFURLRef u = url_for(media, name);
    ExtAudioFileRef ef = NULL;
    OSStatus st = ExtAudioFileOpenURL(u, &ef);
    CFRelease(u);
    snprintf(tag, sizeof tag, "ext_open[%s]", tagname);
    snprintf(d, sizeof d, "status=%d file=%s", (int)st, name);
    check(st == noErr && ef, tag, d);
    if (st != noErr)
        return;
    AudioStreamBasicDescription ff = {};
    UInt32 sz = sizeof ff;
    OSStatus s1 = ExtAudioFileGetProperty(ef, kExtAudioFileProperty_FileDataFormat, &sz, &ff);
    SInt64 len = 0;
    sz = sizeof len;
    OSStatus s2 = ExtAudioFileGetProperty(ef, kExtAudioFileProperty_FileLengthFrames, &sz, &len);
    OSStatus s3 = ExtAudioFileSetProperty(ef, kExtAudioFileProperty_ClientDataFormat, sizeof client, &client);
    AudioStreamBasicDescription back = {};
    sz = sizeof back;
    OSStatus s4 = ExtAudioFileGetProperty(ef, kExtAudioFileProperty_ClientDataFormat, &sz, &back);
    snprintf(tag, sizeof tag, "ext_formats[%s]", tagname);
    snprintf(d, sizeof d, "status=%d,%d,%d,%d file_format=%s file_rate=%.1f file_length_frames=%lld client_rate=%.1f client_flags=0x%x client_bits=%u",
             (int)s1, (int)s2, (int)s3, (int)s4, fourcc(ff.mFormatID, f1), ff.mSampleRate, (long long)len,
             back.mSampleRate, (unsigned)back.mFormatFlags, (unsigned)back.mBitsPerChannel);
    check(s1 == noErr && s2 == noErr && s3 == noErr && s4 == noErr && back.mSampleRate == client.mSampleRate, tag, d);
    if (s3 != noErr) {
        ExtAudioFileDispose(ef);
        return;
    }
    size_t cap = max_frames * client.mBytesPerFrame, got = 0;
    uint8_t *buf = (uint8_t *)malloc(cap);
    unsigned calls = 0;
    OSStatus rs = noErr;
    while (got < cap && calls < 10000) {
        UInt32 frames = 4096;
        if ((cap - got) / client.mBytesPerFrame < frames)
            frames = (UInt32)((cap - got) / client.mBytesPerFrame);
        AudioBufferList bl;
        bl.mNumberBuffers = 1;
        bl.mBuffers[0].mNumberChannels = 2;
        bl.mBuffers[0].mDataByteSize = frames * client.mBytesPerFrame;
        bl.mBuffers[0].mData = buf + got;
        rs = ExtAudioFileRead(ef, &frames, &bl);
        ++calls;
        if (rs != noErr || frames == 0)
            break;
        got += (size_t)frames * client.mBytesPerFrame;
    }
    snprintf(tag, sizeof tag, "ext_read[%s]", tagname);
    snprintf(d, sizeof d, "last_status=%d calls=%u frames=%zu bytes=%zu fnv64=%016llx", (int)rs, calls,
             got / client.mBytesPerFrame, got, (unsigned long long)fnv(buf, got));
    printf("B13_EXT %s %s\n", tagname, d);
    char file[256];
    snprintf(file, sizeof file, "ext-%s.raw", tagname);
    check(rs == noErr && got > 0 && save(out, file, buf, got), tag, d);
    free(buf);
    st = ExtAudioFileDispose(ef);
    snprintf(tag, sizeof tag, "ext_dispose[%s]", tagname);
    snprintf(d, sizeof d, "status=%d", (int)st);
    check(st == noErr, tag, d);
}

struct feed { const uint8_t *p; size_t n, pos; UInt32 bpf; unsigned calls; };
static OSStatus feed_proc(AudioConverterRef, UInt32 *io, AudioBufferList *bl, AudioStreamPacketDescription **pd, void *u)
{
    struct feed *f = (struct feed *)u;
    size_t avail = (f->n - f->pos) / f->bpf;
    UInt32 n = *io < avail ? *io : (UInt32)avail;
    ++f->calls;
    if (pd)
        *pd = NULL;
    bl->mNumberBuffers = 1;
    bl->mBuffers[0].mNumberChannels = 2;
    bl->mBuffers[0].mData = (void *)(f->p + f->pos);
    bl->mBuffers[0].mDataByteSize = n * f->bpf;
    f->pos += (size_t)n * f->bpf;
    *io = n;
    return noErr;
}

static void converter_cases(const char *out)
{
    char d[512];
    if (!g_wav_packets) {
        check(false, "converter_input", "no demo-s16.wav packets");
        return;
    }
    AudioStreamBasicDescription in = pcm(44100, 16, false, false), outf = pcm(44100, 32, true, false);
    AudioConverterRef c = NULL;
    OSStatus st = AudioConverterNew(&in, &outf, &c);
    snprintf(d, sizeof d, "status=%d", (int)st);
    check(st == noErr && c, "converter_new[s16le->f32]", d);
    if (st == noErr) {
        size_t frames = g_wav_bytes / 4, got = 0;
        uint8_t *o = (uint8_t *)malloc(frames * 8 + 65536);
        struct feed fd = { g_wav_packets, g_wav_bytes, 0, 4, 0 };
        OSStatus rs = noErr;
        unsigned calls = 0;
        while (calls < 10000) {
            UInt32 n = 4096;
            AudioBufferList bl;
            bl.mNumberBuffers = 1;
            bl.mBuffers[0].mNumberChannels = 2;
            bl.mBuffers[0].mDataByteSize = n * 8;
            bl.mBuffers[0].mData = o + got;
            if (got + n * 8 > frames * 8 + 65536)
                break;
            rs = AudioConverterFillComplexBuffer(c, feed_proc, &fd, &n, &bl, NULL);
            ++calls;
            if (rs != noErr || n == 0)
                break;
            got += (size_t)n * 8;
        }
        snprintf(d, sizeof d, "last_status=%d calls=%u input_calls=%u frames=%zu bytes=%zu fnv64=%016llx", (int)rs, calls,
                 fd.calls, got / 8, got, (unsigned long long)fnv(o, got));
        check(rs == noErr && got > 0 && save(out, "conv-s16le-f32.raw", o, got), "converter_fill[s16le->f32]", d);
        free(o);
        st = AudioConverterDispose(c);
        snprintf(d, sizeof d, "status=%d", (int)st);
        check(st == noErr, "converter_dispose[s16le->f32]", d);
    }
}

static int convertbuffer_case(const char *media, const char *out)
{
    char d[512];
    audiofile_case(media, out, "demo-s16.wav", true);
    if (!g_wav_packets)
        return 3;
    AudioStreamBasicDescription in = pcm(44100, 16, false, false), be = pcm(44100, 16, false, true);
    AudioConverterRef c = NULL;
    OSStatus st = AudioConverterNew(&in, &be, &c);
    printf("B13_OBS convertbuffer_enter new_status=%d\n", (int)st);
    fflush(stdout);
    if (st == noErr) {
        UInt32 osz = 4096 * 4;
        uint8_t *o = (uint8_t *)calloc(1, osz);
        OSStatus cs = AudioConverterConvertBuffer(c, 4096 * 4, g_wav_packets, &osz, o);
        snprintf(d, sizeof d, "new_status=0 convert_status=%d out_bytes=%u", (int)cs, (unsigned)osz);
        note("converter_convertbuffer[s16le->s16be]", d);
        free(o);
        AudioConverterDispose(c);
    } else {
        snprintf(d, sizeof d, "new_status=%d", (int)st);
        note("converter_convertbuffer[s16le->s16be]", d);
    }
    return 0;
}

static void list_images(void)
{
    uint32_t n = _dyld_image_count();
    for (uint32_t i = 0; i < n; ++i) {
        const char *p = _dyld_get_image_name(i);
        if (strstr(p, "AudioToolbox") || strstr(p, "CoreAudio") || strstr(p, "AFAVFormat") || strstr(p, "/native/"))
            printf("B13_LOADED %s\n", p);
    }
}

static int probe(const char *media, const char *out)
{
    char d[256];
    image("AudioFileOpenURL", (const void *)AudioFileOpenURL);
    image("ExtAudioFileRead", (const void *)ExtAudioFileRead);
    image("AudioConverterNew", (const void *)AudioConverterNew);
    image("AudioDeviceStart", (const void *)AudioDeviceStart);
    UInt32 sz = 0;
    OSStatus st = AudioFileGetGlobalInfoSize(kAudioFileGlobalInfo_ReadableTypes, 0, NULL, &sz);
    UInt32 types[64] = {};
    if (st == noErr && sz <= sizeof types)
        st = AudioFileGetGlobalInfo(kAudioFileGlobalInfo_ReadableTypes, 0, NULL, &sz, types);
    printf("B13_READABLE status=%d", (int)st);
    for (UInt32 i = 0; i < sz / 4 && i < 64; ++i) {
        char b[16];
        printf(" %s", fourcc(types[i], b));
    }
    printf("\n");
    snprintf(d, sizeof d, "status=%d count=%u", (int)st, (unsigned)(sz / 4));
    check(st == noErr && sz >= 4, "readable_types", d);

    audiofile_case(media, out, "demo-s16.wav", true);
    audiofile_case(media, out, "demo-s16.aiff", false);
    audiofile_case(media, out, "demo-s16.caf", false);
    audiofile_case(media, out, "demo-ulaw.wav", false);
    negative_case(media, out, "missing.wav");
    negative_case(media, out, "bad-garbage.wav");
    negative_case(media, out, "bad-empty.wav");
    negative_case(media, out, "bad-trunc.wav");
    list_images();

    ext_case(media, out, "wav-f32", "demo-s16.wav", pcm(44100, 32, true, false), 88200 + 8192);
    ext_case(media, out, "ulaw-s16", "demo-ulaw.wav", pcm(44100, 16, false, false), 88200 + 8192);
    ext_case(media, out, "aiff-s16le", "demo-s16.aiff", pcm(44100, 16, false, false), 88200 + 8192);
    ext_case(media, out, "wav-f32-48k", "demo-s16.wav", pcm(48000, 32, true, false), 96000 + 8192);
    converter_cases(out);
    list_images();
    printf("B13_SUMMARY checks=%u failures=%u\n", checks, failures);
    return failures > 100 ? 100 : (int)failures;
}

/* ---- D: decoded PCM -> CoreAudio (B12 scheme) ----------------------------------- */
static double now_s(void)
{
    struct timeval tv;
    gettimeofday(&tv, NULL);
    return tv.tv_sec + tv.tv_usec / 1e6;
}
static const uint8_t *g_pcm;
static size_t g_total;
static volatile size_t g_pos;
static volatile int g_ended, g_running;
static volatile unsigned g_callbacks, g_after_end, g_bad_shape;
static volatile size_t g_last_partial_frames;
static volatile uint64_t g_fnv = 0xcbf29ce484222325ULL;

static OSStatus ioproc(AudioObjectID, const AudioTimeStamp *, const AudioBufferList *, const AudioTimeStamp *,
                       AudioBufferList *o, const AudioTimeStamp *, void *)
{
    ++g_callbacks;
    if (!o || o->mNumberBuffers != 1 || !o->mBuffers[0].mData) {
        ++g_bad_shape;
        return noErr;
    }
    uint8_t *dst = (uint8_t *)o->mBuffers[0].mData;
    size_t want = o->mBuffers[0].mDataByteSize, have = g_total - g_pos, n = want < have ? want : have;
    if (g_ended)
        ++g_after_end;
    memcpy(dst, g_pcm + g_pos, n);
    memset(dst + n, 0, want - n);
    uint64_t h = g_fnv;
    for (size_t i = 0; i < n; ++i) { h ^= dst[i]; h *= 0x100000001b3ULL; }
    g_fnv = h;
    g_pos += n;
    if (!g_ended && g_pos == g_total) {
        g_last_partial_frames = n / 4;
        g_ended = 1;
    }
    return noErr;
}

static void play_to_end(AudioDeviceID dev, AudioDeviceIOProcID id, double expect_s, const char *tag)
{
    char d[512];
    g_pos = 0;
    g_ended = 0;
    g_after_end = 0;
    unsigned cb0 = g_callbacks;
    g_running = 1;
    double t0 = now_s();
    OSStatus st = AudioDeviceStart(dev, id);
    snprintf(d, sizeof d, "status=%d", (int)st);
    check(st == noErr, tag, d);
    if (st != noErr)
        return;
    while (!g_ended && now_s() - t0 < expect_s + 5.0)
        usleep(5000);
    double t_end = now_s() - t0;
    usleep(400000);
    g_running = 0;
    st = AudioDeviceStop(dev, id);
    snprintf(d, sizeof d, "ended=%d elapsed_to_end_s=%.3f expected_s=%.3f delivered_bytes=%zu total=%zu "
             "last_partial_frames=%zu callbacks=%u silent_callbacks_after_end=%u stop_status=%d",
             (int)g_ended, t_end, expect_s, (size_t)g_pos, g_total, (size_t)g_last_partial_frames,
             g_callbacks - cb0, g_after_end, (int)st);
    check(g_ended && g_pos == g_total && st == noErr && t_end > expect_s * 0.9 && t_end < expect_s + 1.5, "natural_end", d);
}

static int play(const char *media, const char *out, const char *mode, const char *file)
{
    char d[512];
    image("ExtAudioFileRead", (const void *)ExtAudioFileRead);
    image("AudioConverterNew", (const void *)AudioConverterNew);
    image("AudioDeviceStart", (const void *)AudioDeviceStart);
    /* Decode the whole file before Play, to S16LE, through AudioToolbox. */
    CFURLRef u = url_for(media, file);
    ExtAudioFileRef ef = NULL;
    OSStatus st = ExtAudioFileOpenURL(u, &ef);
    CFRelease(u);
    AudioStreamBasicDescription client = pcm(44100, 16, false, false);
    OSStatus s2 = st == noErr ? ExtAudioFileSetProperty(ef, kExtAudioFileProperty_ClientDataFormat, sizeof client, &client) : st;
    size_t cap = (88200 + 8192) * 4, got = 0;
    uint8_t *buf = (uint8_t *)malloc(cap);
    OSStatus rs = s2;
    while (rs == noErr && got < cap) {
        UInt32 frames = (UInt32)((cap - got) / 4 < 4096 ? (cap - got) / 4 : 4096);
        AudioBufferList bl;
        bl.mNumberBuffers = 1;
        bl.mBuffers[0].mNumberChannels = 2;
        bl.mBuffers[0].mDataByteSize = frames * 4;
        bl.mBuffers[0].mData = buf + got;
        rs = ExtAudioFileRead(ef, &frames, &bl);
        if (rs != noErr || frames == 0)
            break;
        got += (size_t)frames * 4;
    }
    if (ef)
        ExtAudioFileDispose(ef);
    uint64_t pcm_fnv = fnv(buf, got);
    snprintf(d, sizeof d, "file=%s open=%d client=%d read=%d frames=%zu bytes=%zu fnv64=%016llx", file, (int)st, (int)s2, (int)rs,
             got / 4, got, (unsigned long long)pcm_fnv);
    check(st == noErr && s2 == noErr && rs == noErr && got == 88200 * 4 && save(out, "decoded.s16le", buf, got), "decode_to_s16le", d);
    if (got != 88200 * 4)
        return 3;

    AudioObjectPropertyAddress a = { kAudioHardwarePropertyDefaultOutputDevice, kAudioObjectPropertyScopeGlobal,
                                     kAudioObjectPropertyElementMaster };
    AudioDeviceID dev = 0;
    UInt32 sz = sizeof dev;
    st = AudioObjectGetPropertyData(kAudioObjectSystemObject, &a, 0, NULL, &sz, &dev);
    snprintf(d, sizeof d, "status=%d device=%u", (int)st, (unsigned)dev);
    check(st == noErr && dev != 0, "default_output_device", d);
    if (st != noErr || !dev)
        return 5;
    AudioStreamBasicDescription f = client, r = {};
    a.mSelector = kAudioDevicePropertyStreamFormat;
    a.mScope = kAudioDevicePropertyScopeOutput;
    st = AudioObjectSetPropertyData(dev, &a, 0, NULL, sizeof f, &f);
    sz = sizeof r;
    OSStatus st2 = AudioObjectGetPropertyData(dev, &a, 0, NULL, &sz, &r);
    snprintf(d, sizeof d, "set=%d get=%d rate=%.0f flags=0x%x channels=%u bits=%u", (int)st, (int)st2, r.mSampleRate,
             (unsigned)r.mFormatFlags, (unsigned)r.mChannelsPerFrame, (unsigned)r.mBitsPerChannel);
    check(st == noErr && st2 == noErr && r.mSampleRate == 44100 && r.mChannelsPerFrame == 2 && r.mBitsPerChannel == 16 &&
          !(r.mFormatFlags & kAudioFormatFlagIsBigEndian) && !(r.mFormatFlags & kAudioFormatFlagIsFloat),
          "device_format_is_decoded_format", d);
    g_pcm = buf;
    g_total = got;
    AudioDeviceIOProcID id = NULL;
    st = AudioDeviceCreateIOProcID(dev, ioproc, NULL, &id);
    snprintf(d, sizeof d, "status=%d", (int)st);
    check(st == noErr && id, "create_ioproc", d);
    if (st != noErr)
        return 6;
    double expect = 88200.0 / 44100.0;
    if (!strcmp(mode, "stoprestart")) {
        g_pos = 0;
        g_running = 1;
        st = AudioDeviceStart(dev, id);
        snprintf(d, sizeof d, "status=%d", (int)st);
        check(st == noErr, "first_play", d);
        usleep(700000);
        g_running = 0;
        st = AudioDeviceStop(dev, id);
        size_t pos_stop = g_pos;
        unsigned cb_stop = g_callbacks;
        usleep(600000);
        snprintf(d, sizeof d, "stop_status=%d pos_at_stop=%zu callbacks_at_stop=%u callbacks_after_stop=%u pos_after=%zu",
                 (int)st, pos_stop, cb_stop, g_callbacks - cb_stop, (size_t)g_pos);
        check(st == noErr && pos_stop > 0 && pos_stop < got && g_callbacks == cb_stop && g_pos == pos_stop,
              "stop_silences_ioproc", d);
        g_fnv = 0xcbf29ce484222325ULL;
        play_to_end(dev, id, expect, "second_play");
    } else {
        g_fnv = 0xcbf29ce484222325ULL;
        play_to_end(dev, id, expect, "play");
    }
    snprintf(d, sizeof d, "delivered_fnv64=%016llx decoded_fnv64=%016llx bad_shape=%u", (unsigned long long)g_fnv,
             (unsigned long long)pcm_fnv, g_bad_shape);
    check(g_fnv == pcm_fnv && g_bad_shape == 0, "delivered_bytes_equal_decoded", d);
    st = AudioDeviceDestroyIOProcID(dev, id);
    snprintf(d, sizeof d, "status=%d", (int)st);
    check(st == noErr, "destroy_ioproc", d);
    free(buf);
    printf("B13_SUMMARY checks=%u failures=%u\n", checks, failures);
    return failures > 100 ? 100 : (int)failures;
}

int main(int argc, char **argv)
{
    printf("B13_ABI pointer_bits=%zu\n", sizeof(void *) * 8);
    fflush(stdout);
    if (argc == 4 && !strcmp(argv[1], "probe"))
        return probe(argv[2], argv[3]);
    if (argc == 4 && !strcmp(argv[1], "convertbuffer"))
        return convertbuffer_case(argv[2], argv[3]);
    if (argc == 5 || argc == 6) {
        if (!strcmp(argv[1], "play"))
            return play(argv[2], argv[3], argv[4], argc == 6 ? argv[5] : "demo-s16.aiff");
    }
    fprintf(stderr, "usage: b13-atb probe MEDIA OUT | convertbuffer MEDIA OUT | play MEDIA OUT play|stoprestart [FILE]\n");
    return 2;
}
