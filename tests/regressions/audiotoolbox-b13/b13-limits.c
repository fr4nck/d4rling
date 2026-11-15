/* SPDX-License-Identifier: GPL-3.0-or-later
 * B13 / ATB-FIX2-R2b review: size limits of AudioConverterConvertBuffer and
 * AudioConverterConvertComplexBuffer before any conversion. Private review probe,
 * separate from the 27 frozen fix2 controls. Built as C++ (tools/build.sh, CXX=1).
 *
 *   b13-limits
 *     1. destination descriptions whose bytes-per-frame check overflows in 32 bits
 *        (channels 0x40000001 x 4 bytes, 0x80000001 x 2 bytes): the call must fail,
 *        report no output and write nothing (canaries over the whole buffer);
 *     2. the same overflow on the source side: AudioConverterNew must refuse it;
 *     3. frame counts whose byte sizes exceed 32 bits in ConvertComplexBuffer:
 *        refused before any read or write.
 */
#include <AudioToolbox/AudioToolbox.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

static unsigned checks, failures;
static void check(bool ok, const char *name, const char *detail)
{
    ++checks;
    if (!ok)
        ++failures;
    printf("B13LIM %s %s %s\n", name, ok ? "PASS" : "FAIL", detail);
    fflush(stdout);
}

static AudioStreamBasicDescription pcm(UInt32 bits, UInt32 channels, UInt32 bytesPerFrame)
{
    AudioStreamBasicDescription d;
    memset(&d, 0, sizeof d);
    d.mSampleRate = 48000;
    d.mFormatID = kAudioFormatLinearPCM;
    d.mFormatFlags = kAudioFormatFlagIsSignedInteger | kAudioFormatFlagIsPacked;
    d.mFramesPerPacket = 1;
    d.mBitsPerChannel = bits;
    d.mChannelsPerFrame = channels;
    d.mBytesPerFrame = bytesPerFrame;
    d.mBytesPerPacket = bytesPerFrame;
    return d;
}

static bool all(const uint8_t *p, size_t n, uint8_t v)
{
    for (size_t i = 0; i < n; ++i)
        if (p[i] != v)
            return false;
    return true;
}

static void overflowDestination(const char *name, UInt32 bits, UInt32 channels, UInt32 bytesPerFrame)
{
    char d[200];
    AudioStreamBasicDescription src = pcm(16, 2, 4), dst = pcm(bits, channels, bytesPerFrame);
    AudioConverterRef c = nullptr;
    OSStatus st = AudioConverterNew(&src, &dst, &c);
    if (st != noErr || !c) {
        snprintf(d, sizeof d, "new=%d (refused at creation)", (int) st);
        check(st != noErr && !c, name, d);
        return;
    }
    int16_t in[32];
    for (int i = 0; i < 32; ++i)
        in[i] = (int16_t) (i * 1000 - 16000);
    uint8_t out[256];
    memset(out, 0xA5, sizeof out);
    UInt32 size = 64;   /* 16 frames x the declared 4 bytes */
    st = AudioConverterConvertBuffer(c, sizeof in, in, &size, out);
    bool untouched = all(out, sizeof out, 0xA5);
    snprintf(d, sizeof d, "new=0 convert=%d size=%u untouched=%d", (int) st, (unsigned) size, untouched);
    check(st != noErr && size == 0 && untouched, name, d);
    AudioConverterDispose(c);
}

static void overflowSource(const char *name, UInt32 bits, UInt32 channels, UInt32 bytesPerFrame)
{
    char d[200];
    AudioStreamBasicDescription src = pcm(bits, channels, bytesPerFrame), dst = pcm(16, 2, 4);
    AudioConverterRef c = nullptr;
    OSStatus st = AudioConverterNew(&src, &dst, &c);
    if (st == noErr && c) {
        int16_t in[32] = { 0 };
        uint8_t out[256];
        memset(out, 0xA5, sizeof out);
        UInt32 size = 64;
        OSStatus cv = AudioConverterConvertBuffer(c, 64, in, &size, out);
        bool untouched = all(out, sizeof out, 0xA5);
        snprintf(d, sizeof d, "new=0 convert=%d size=%u untouched=%d", (int) cv, (unsigned) size, untouched);
        check(cv != noErr && untouched, name, d);
        AudioConverterDispose(c);
        return;
    }
    snprintf(d, sizeof d, "new=%d (refused at creation)", (int) st);
    check(st != noErr && !c, name, d);
}

static void hugeFrames(void)
{
    char d[200];
    AudioStreamBasicDescription src = pcm(16, 2, 4), dst = pcm(32, 2, 8);
    AudioConverterRef c = nullptr;
    OSStatus st = AudioConverterNew(&src, &dst, &c);
    if (st != noErr || !c) {
        snprintf(d, sizeof d, "new=%d", (int) st);
        check(false, "huge_frames_setup", d);
        return;
    }
    uint8_t inData[64], outData[256];
    memset(inData, 0x11, sizeof inData);

    /* 0x40000000 frames x 4 bytes = 2^32: more than any input buffer can declare */
    AudioBufferList in, out;
    in.mNumberBuffers = out.mNumberBuffers = 1;
    in.mBuffers[0].mNumberChannels = out.mBuffers[0].mNumberChannels = 2;
    in.mBuffers[0].mData = inData;
    in.mBuffers[0].mDataByteSize = 0xFFFFFFFCu;
    memset(outData, 0xA5, sizeof outData);
    out.mBuffers[0].mData = outData;
    out.mBuffers[0].mDataByteSize = sizeof outData;
    st = AudioConverterConvertComplexBuffer(c, 0x40000000u, &in, &out);
    bool untouched = all(outData, sizeof outData, 0xA5);
    snprintf(d, sizeof d, "status=%d size=%u untouched=%d", (int) st, (unsigned) out.mBuffers[0].mDataByteSize, untouched);
    check(st == kAudioConverterErr_InvalidInputSize && out.mBuffers[0].mDataByteSize == sizeof outData && untouched,
          "complex_input_bytes_over_32_bits", d);

    /* 0x20000000 frames: input 2^31 bytes declared, output 2^32 bytes needed */
    in.mBuffers[0].mDataByteSize = 0x80000000u;
    memset(outData, 0xA5, sizeof outData);
    out.mBuffers[0].mDataByteSize = 0xFFFFFFF8u;   /* declared, never reached */
    st = AudioConverterConvertComplexBuffer(c, 0x20000000u, &in, &out);
    untouched = all(outData, sizeof outData, 0xA5);
    snprintf(d, sizeof d, "status=%d size=%u untouched=%d", (int) st, (unsigned) out.mBuffers[0].mDataByteSize, untouched);
    check(st == kAudioConverterErr_InvalidOutputSize && out.mBuffers[0].mDataByteSize == 0 && untouched,
          "complex_output_bytes_over_32_bits", d);

    /* ConvertBuffer: largest frame-aligned input, small output -> refused without reading */
    UInt32 size = sizeof outData;
    memset(outData, 0xA5, sizeof outData);
    st = AudioConverterConvertBuffer(c, 0xFFFFFFFCu, inData, &size, outData);
    untouched = all(outData, sizeof outData, 0xA5);
    snprintf(d, sizeof d, "status=%d size=%u untouched=%d", (int) st, (unsigned) size, untouched);
    check(st == kAudioConverterErr_InvalidOutputSize && size == 0 && untouched, "convertbuffer_max_input", d);
    AudioConverterDispose(c);
}

int main(void)
{
    overflowDestination("dst_s32_ch0x40000001_bpf4", 32, 0x40000001u, 4);
    overflowDestination("dst_s16_ch0x80000001_bpf2", 16, 0x80000001u, 2);
    overflowDestination("dst_s64_ch0x20000001_bpf8", 64, 0x20000001u, 8);
    overflowSource("src_s32_ch0x40000001_bpf4", 32, 0x40000001u, 4);
    overflowSource("src_s16_ch0x80000001_bpf2", 16, 0x80000001u, 2);
    hugeFrames();
    printf("B13LIM_SUMMARY checks=%u failures=%u\n", checks, failures);
    return failures ? 1 : 0;
}
