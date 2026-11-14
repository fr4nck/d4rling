/* SPDX-License-Identifier: GPL-3.0-or-later
 * QT-B12-A: CoreAudio (production framework, PulseAudio backend) probe.
 * Reports the images that provide CoreAudio, the default output device and
 * its format, then runs an IOProc that writes SILENCE only for a bounded time,
 * counting callbacks. No audible output by construction.
 * Usage: ca-probe [silence_ms]
 */
#include <CoreAudio/CoreAudio.h>
#include <dlfcn.h>
#include <mach-o/dyld.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

static volatile unsigned callbacks, last_bytes, last_buffers;

static OSStatus silence(AudioObjectID dev, const AudioTimeStamp *now, const AudioBufferList *in,
                        const AudioTimeStamp *in_time, AudioBufferList *out, const AudioTimeStamp *out_time,
                        void *ctx)
{
    UInt32 i;
    (void)dev; (void)now; (void)in; (void)in_time; (void)out_time; (void)ctx;
    for (i = 0; out && i < out->mNumberBuffers; ++i)
        memset(out->mBuffers[i].mData, 0, out->mBuffers[i].mDataByteSize);
    if (out && out->mNumberBuffers) {
        last_bytes = out->mBuffers[0].mDataByteSize;
        last_buffers = out->mNumberBuffers;
    }
    ++callbacks;
    return noErr;
}

int main(int argc, char **argv)
{
    AudioObjectPropertyAddress a = { kAudioHardwarePropertyDefaultOutputDevice, kAudioObjectPropertyScopeGlobal,
                                     kAudioObjectPropertyElementMaster };
    AudioDeviceID dev = 0;
    UInt32 size = sizeof dev, frames = 0;
    AudioStreamBasicDescription f;
    AudioDeviceIOProcID id = NULL;
    Dl_info di;
    char name[256] = "";
    OSStatus st;
    int ms = argc > 1 ? atoi(argv[1]) : 0;
    uint32_t i;

    printf("CA_ABI pointer_bits=%zu\n", sizeof(void *) * 8);
    printf("CA_ENV PULSE_SERVER=%s\n", getenv("PULSE_SERVER") ? getenv("PULSE_SERVER") : "(unset)");
    if (dladdr((const void *)AudioObjectGetPropertyData, &di))
        printf("CA_IMAGE AudioObjectGetPropertyData %s\n", di.dli_fname);
    st = AudioObjectGetPropertyData(kAudioObjectSystemObject, &a, 0, NULL, &size, &dev);
    printf("CA_DEFAULT_OUTPUT status=%d device=%u\n", (int)st, (unsigned)dev);
    for (i = 0; i < _dyld_image_count(); ++i)
        if (strstr(_dyld_get_image_name(i), "CoreAudio") || strstr(_dyld_get_image_name(i), "pulse") ||
            strstr(_dyld_get_image_name(i), "elfloader"))
            printf("CA_LOADED %s\n", _dyld_get_image_name(i));
    if (st != noErr || !dev) {
        printf("CA_RESULT NO_DEVICE\n");
        return 10;
    }
    a.mSelector = kAudioDevicePropertyDeviceName;
    a.mScope = kAudioDevicePropertyScopeOutput;
    size = sizeof name - 1;
    st = AudioObjectGetPropertyData(dev, &a, 0, NULL, &size, name);
    printf("CA_DEVICE_NAME status=%d name=%s\n", (int)st, name);
    a.mSelector = kAudioDevicePropertyStreamFormat;
    size = sizeof f;
    memset(&f, 0, sizeof f);
    st = AudioObjectGetPropertyData(dev, &a, 0, NULL, &size, &f);
    printf("CA_FORMAT status=%d rate=%.1f flags=0x%x bits=%u channels=%u bytes_per_frame=%u\n", (int)st,
           f.mSampleRate, (unsigned)f.mFormatFlags, (unsigned)f.mBitsPerChannel, (unsigned)f.mChannelsPerFrame,
           (unsigned)f.mBytesPerFrame);
    a.mSelector = kAudioDevicePropertyBufferFrameSize;
    size = sizeof frames;
    st = AudioObjectGetPropertyData(dev, &a, 0, NULL, &size, &frames);
    printf("CA_BUFFER_FRAMES status=%d frames=%u\n", (int)st, (unsigned)frames);
    if (ms <= 0)
        return 0;
    st = AudioDeviceCreateIOProcID(dev, silence, NULL, &id);
    printf("CA_CREATE_IOPROC status=%d\n", (int)st);
    if (st != noErr)
        return 11;
    st = AudioDeviceStart(dev, id);
    printf("CA_START status=%d\n", (int)st);
    usleep((useconds_t)ms * 1000);
    st = AudioDeviceStop(dev, id);
    printf("CA_STOP status=%d callbacks=%u last_bytes=%u buffers=%u\n", (int)st, callbacks, last_bytes, last_buffers);
    st = AudioDeviceDestroyIOProcID(dev, id);
    printf("CA_DESTROY status=%d\n", (int)st);
    printf("CA_RESULT %s\n", callbacks > 0 ? "CALLBACKS" : "NO_CALLBACKS");
    return callbacks > 0 ? 0 : 12;
}
