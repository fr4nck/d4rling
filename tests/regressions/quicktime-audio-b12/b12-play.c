/* SPDX-License-Identifier: GPL-3.0-or-later
 * QT-B12-C/D: MOV -> QuickTime (NewMovieFromDataRef, GetMediaSample) ->
 * CoreAudio HAL (production framework, PulseAudio backend).
 *
 * The whole PCM is read through GetMediaSample before Play (no I/O,
 * allocation or lock in the IOProc). The output device is set to the MOV's
 * own format (16-bit big-endian signed, interleaved, rate and channels of the
 * media), so the IOProc copies GetMediaSample's bytes unchanged; frames after
 * the end of the media are zero. No other PCM source exists in this program.
 *
 * Usage: b12-play MOV OUT_DIR play|stoprestart
 *   play         Play to the natural end of the track, then Stop and close.
 *   stoprestart  Play 0.7 s, Stop, 0.6 s without callbacks, second Play from
 *                the start to the natural end, Stop, close.
 * Built as C++ (Darling's CoreAudio headers). -DB12_NO_AUDIO builds the
 * QuickTime-only part (open + GetMediaSample + gms.pcm), without CoreAudio.
 */
#include <QuickTime/QuickTime.h>
#include <CarbonCore/MacMemory.h>
#ifndef B12_NO_AUDIO
#include <CoreAudio/CoreAudio.h>
#endif
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
    printf("B12 %s %s %s\n", name, ok ? "PASS" : "FAIL", detail);
    fflush(stdout);
}

static uint64_t fnv_step(uint64_t h, const uint8_t *p, size_t n)
{
    for (size_t i = 0; i < n; ++i) { h ^= p[i]; h *= 0x100000001b3ULL; }
    return h;
}

static double now_s(void)
{
    struct timeval tv;
    gettimeofday(&tv, NULL);
    return tv.tv_sec + tv.tv_usec / 1e6;
}

#ifndef B12_NO_AUDIO
/* State shared with the IOProc: written by it, read by main after Stop. */
static const uint8_t *g_pcm;
static size_t g_total, g_frame_bytes;
static volatile size_t g_pos;
static volatile int g_ended, g_running;
static volatile unsigned g_callbacks, g_after_end, g_after_stop, g_bad_shape;
static volatile size_t g_last_partial_frames;
static volatile uint64_t g_fnv = 0xcbf29ce484222325ULL;

static OSStatus ioproc(AudioObjectID, const AudioTimeStamp *, const AudioBufferList *, const AudioTimeStamp *,
                       AudioBufferList *out, const AudioTimeStamp *, void *)
{
    if (!g_running)
        ++g_after_stop;
    ++g_callbacks;
    if (!out || out->mNumberBuffers != 1 || !out->mBuffers[0].mData) {
        ++g_bad_shape;
        return noErr;
    }
    uint8_t *dst = (uint8_t *)out->mBuffers[0].mData;
    size_t want = out->mBuffers[0].mDataByteSize, have = g_total - g_pos, n = want < have ? want : have;
    if (g_ended)
        ++g_after_end;
    memcpy(dst, g_pcm + g_pos, n);
    memset(dst + n, 0, want - n);
    g_fnv = fnv_step(g_fnv, dst, n);
    g_pos += n;
    if (!g_ended && g_pos == g_total) {
        g_last_partial_frames = n / g_frame_bytes;
        g_ended = 1;
    }
    return noErr;
}

#endif

static uint8_t *read_file(const char *path, size_t *n)
{
    FILE *f = fopen(path, "rb");
    long size;
    uint8_t *p = NULL;
    if (!f)
        return NULL;
    if (!fseek(f, 0, SEEK_END) && (size = ftell(f)) > 0 && !fseek(f, 0, SEEK_SET)) {
        p = (uint8_t *)malloc((size_t)size);
        if (p && fread(p, 1, (size_t)size, f) != (size_t)size) { free(p); p = NULL; }
        *n = (size_t)size;
    }
    fclose(f);
    return p;
}

#ifndef B12_NO_AUDIO
/* Play from position 0 until the natural end (or a bounded timeout). */
static int play_to_end(AudioDeviceID dev, AudioDeviceIOProcID id, double expect_s, const char *tag)
{
    char d[256];
    g_pos = 0;
    g_ended = 0;
    g_after_end = 0;
    unsigned cb0 = g_callbacks;
    g_running = 1;
    double t0 = now_s();
    OSStatus st = AudioDeviceStart(dev, id);
    snprintf(d, sizeof d, "status=%d", (int)st);
    check(st == noErr, tag, d);
    if (st != noErr) {
        g_running = 0;
        return 0;
    }
    while (!g_ended && now_s() - t0 < expect_s + 5.0)
        usleep(5000);
    double t_end = now_s() - t0;
    usleep(400000); /* let the tail reach the speakers before Stop */
    g_running = 0;
    st = AudioDeviceStop(dev, id);
    snprintf(d, sizeof d, "ended=%d elapsed_to_end_s=%.3f expected_s=%.3f delivered_bytes=%zu total=%zu "
             "last_partial_frames=%zu callbacks=%u silent_callbacks_after_end=%u stop_status=%d",
             (int)g_ended, t_end, expect_s, (size_t)g_pos, g_total, (size_t)g_last_partial_frames,
             g_callbacks - cb0, g_after_end, (int)st);
    check(g_ended && g_pos == g_total && st == noErr && t_end > expect_s * 0.9 && t_end < expect_s + 1.5,
          "natural_end", d);
    return g_ended;
}

#endif

int main(int argc, char **argv)
{
    char d[512];
    if (argc != 4)
        return 2;
    const char *mode = argv[3];
    printf("B12_ABI pointer_bits=%zu mode=%s\n", sizeof(void *) * 8, mode);
    Dl_info di;
    if (dladdr((const void *)GetMediaSample, &di)) printf("B12_IMAGE GetMediaSample %s\n", di.dli_fname);
#ifndef B12_NO_AUDIO
    if (dladdr((const void *)AudioDeviceStart, &di)) printf("B12_IMAGE AudioDeviceStart %s\n", di.dli_fname);
#endif
    if (dladdr((const void *)GetHandleSize, &di)) printf("B12_IMAGE GetHandleSize %s\n", di.dli_fname);

    /* ---- QuickTime: open and read the whole sound media. */
    size_t mov_n = 0;
    uint8_t *mov = read_file(argv[1], &mov_n);
    snprintf(d, sizeof d, "bytes=%zu", mov_n);
    check(mov != NULL, "read_mov", d);
    if (!mov)
        return 3;
    check(EnterMovies() == noErr, "enter_movies", "");
    PointerDataRefRecord rec = { mov, (Size)mov_n };
    Handle ref = NewHandle((long)sizeof rec);
    memcpy(*ref, &rec, sizeof rec);
    Movie m = NULL;
    OSErr e = NewMovieFromDataRef(&m, 0, NULL, ref, PointerDataHandlerSubType);
    DisposeHandle(ref);
    Track t = e == noErr ? GetMovieIndTrack(m, 1) : NULL;
    Media md = t ? GetTrackMedia(t) : NULL;
    snprintf(d, sizeof d, "status=%d tracks=%ld media_scale=%ld samples=%ld movie_scale=%ld movie_duration=%ld", e,
             m ? (long)GetMovieTrackCount(m) : -1L, md ? (long)GetMediaTimeScale(md) : -1L,
             md ? (long)GetMediaSampleCount(md) : -1L, m ? (long)GetMovieTimeScale(m) : -1L,
             m ? (long)GetMovieDuration(m) : -1L);
    check(md != NULL, "open_movie", d);
    if (!md)
        return 4;
    memset(mov, 0x5A, mov_n); /* the movie owns its samples */
    free(mov);
    size_t frames = (size_t)GetMediaSampleCount(md);
    TimeScale rate = GetMediaTimeScale(md);
    Handle h = NewHandle(0);
    uint8_t *pcm = (uint8_t *)malloc(frames * 4 + 1);
    size_t got = 0, calls = 0, last = 0, max_call = 0;
    SInt32 size = 0, n = 0, idx = 0;
    TimeValue at = 0, st_time = 0, dur = 0;
    SInt16 flags = -1;
    bool shape_ok = true;
    while ((size_t)at < frames && calls < 64) {
        e = GetMediaSample(md, h, 0, &size, at, &st_time, &dur, NULL, &idx, 0, &n, &flags);
        if (e != noErr || n <= 0 || st_time != at || dur != 1 || flags != 0 || got + (size_t)size > frames * 4) {
            shape_ok = false;
            break;
        }
        memcpy(pcm + got, *h, (size_t)size);
        got += (size_t)size;
        last = (size_t)size;
        max_call = (size_t)size > max_call ? (size_t)size : max_call;
        at += n;
        ++calls;
    }
    size_t frame_bytes = got && frames ? got / frames : 0;
    snprintf(d, sizeof d, "status=%d calls=%zu bytes=%zu frames=%zu rate=%ld frame_bytes=%zu last_call_bytes=%zu max_call_bytes=%zu",
             e, calls, got, frames, (long)rate, frame_bytes, last, max_call);
    check(shape_ok && (size_t)at == frames && max_call <= 65536 && frame_bytes == 4, "getmediasample_all", d);
    uint64_t pcm_fnv = fnv_step(0xcbf29ce484222325ULL, pcm, got);
    printf("B12_PCM bytes=%zu fnv64=%016llx\n", got, (unsigned long long)pcm_fnv);
    {
        char path[4096];
        snprintf(path, sizeof path, "%s/gms.pcm", argv[2]);
        FILE *f = fopen(path, "wb");
        check(f && fwrite(pcm, 1, got, f) == got && fclose(f) == 0, "write_gms_pcm", path);
    }
    DisposeHandle(h);
#ifdef B12_NO_AUDIO
    DisposeMovie(m);
    ExitMovies();
    free(pcm);
    printf("B12_SUMMARY checks=%u failures=%u\n", checks, failures);
    if (!failures)
        printf("B12_GMS_OK\n");
    return failures > 100 ? 100 : (int)failures;
#else

    /* ---- CoreAudio: default output in the media's own format. */
    AudioObjectPropertyAddress a = { kAudioHardwarePropertyDefaultOutputDevice, kAudioObjectPropertyScopeGlobal,
                                     kAudioObjectPropertyElementMaster };
    AudioDeviceID dev = 0;
    UInt32 sz = sizeof dev;
    OSStatus st = AudioObjectGetPropertyData(kAudioObjectSystemObject, &a, 0, NULL, &sz, &dev);
    snprintf(d, sizeof d, "status=%d device=%u", (int)st, (unsigned)dev);
    check(st == noErr && dev != 0, "default_output_device", d);
    if (st != noErr || !dev)
        return 5;
    AudioStreamBasicDescription f = {};
    f.mSampleRate = rate;
    f.mFormatID = kAudioFormatLinearPCM;
    f.mFormatFlags = kAudioFormatFlagIsSignedInteger | kAudioFormatFlagIsBigEndian | kAudioFormatFlagIsPacked;
    f.mChannelsPerFrame = 2;
    f.mBitsPerChannel = 16;
    f.mFramesPerPacket = 1;
    f.mBytesPerFrame = f.mBytesPerPacket = 4;
    a.mSelector = kAudioDevicePropertyStreamFormat;
    a.mScope = kAudioDevicePropertyScopeOutput;
    st = AudioObjectSetPropertyData(dev, &a, 0, NULL, sizeof f, &f);
    AudioStreamBasicDescription r = {};
    sz = sizeof r;
    OSStatus st2 = AudioObjectGetPropertyData(dev, &a, 0, NULL, &sz, &r);
    snprintf(d, sizeof d, "set=%d get=%d rate=%.0f flags=0x%x channels=%u bits=%u bytes_per_frame=%u", (int)st, (int)st2,
             r.mSampleRate, (unsigned)r.mFormatFlags, (unsigned)r.mChannelsPerFrame, (unsigned)r.mBitsPerChannel,
             (unsigned)r.mBytesPerFrame);
    check(st == noErr && st2 == noErr && r.mSampleRate == rate && r.mChannelsPerFrame == 2 && r.mBitsPerChannel == 16 &&
          (r.mFormatFlags & kAudioFormatFlagIsBigEndian), "device_format_is_media_format", d);

    g_pcm = pcm;
    g_total = got;
    g_frame_bytes = 4;
    AudioDeviceIOProcID id = NULL;
    st = AudioDeviceCreateIOProcID(dev, ioproc, NULL, &id);
    snprintf(d, sizeof d, "status=%d", (int)st);
    check(st == noErr && id, "create_ioproc", d);
    if (st != noErr)
        return 6;
    double expect = (double)frames / rate;

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
    snprintf(d, sizeof d, "delivered_fnv64=%016llx pcm_fnv64=%016llx bad_shape=%u", (unsigned long long)g_fnv,
             (unsigned long long)pcm_fnv, g_bad_shape);
    check(g_fnv == pcm_fnv && g_bad_shape == 0, "delivered_bytes_equal_getmediasample", d);
    st = AudioDeviceDestroyIOProcID(dev, id);
    snprintf(d, sizeof d, "status=%d", (int)st);
    check(st == noErr, "destroy_ioproc", d);
    DisposeMovie(m);
    ExitMovies();
    free(pcm);
    printf("B12_SUMMARY checks=%u failures=%u\n", checks, failures);
    if (!failures)
        printf("B12_PLAY_OK\n");
    return failures > 100 ? 100 : (int)failures;
#endif
}
