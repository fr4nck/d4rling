/* SPDX-License-Identifier: GPL-3.0-or-later
 * QT-B11E-R3: MOV -> production QuickTime GetMediaSample -> experimental HAL
 * (b06_hal_run from the B11C-R2 hal.o, CoreAudio-B14 / libpulse-B14 private
 * dylibs) -> C10 FIFO -> simulated host. No injection: B11_VECTOR is never set,
 * the HAL receives exactly the bytes of GetMediaSample's handle.
 *
 * Usage: b11e-r3-fifo-chain MOV_DIR V REQUEST_FIFO REPLY_FIFO
 */
#include <QuickTime/QuickTime.h>
#include <CarbonCore/MacMemory.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

extern int b06_hal_run(const unsigned char *pcm, unsigned frames);

static uint64_t fnv64(const unsigned char *p, size_t n)
{
    uint64_t h = 0xcbf29ce484222325ULL;
    size_t i;
    for (i = 0; i < n; ++i) { h ^= p[i]; h *= 0x100000001b3ULL; }
    return h;
}

int main(int argc, char **argv)
{
    char path[4096];
    PointerDataRefRecord rec;
    Handle ref, h;
    Movie m = NULL;
    Track t;
    Media md;
    unsigned char *data;
    long size;
    FILE *f;
    SInt32 bytes = 0, count = 0;
    OSErr e;
    int rc;

    if (argc != 5 || unsetenv("B11_VECTOR") != 0)
        return 2;
    snprintf(path, sizeof path, "%s/mov-%s.mov", argv[1], argv[2]);
    if (!(f = fopen(path, "rb")) || fseek(f, 0, SEEK_END) || (size = ftell(f)) <= 0 || fseek(f, 0, SEEK_SET))
        return 3;
    data = malloc((size_t)size);
    if (!data || fread(data, 1, (size_t)size, f) != (size_t)size)
        return 4;
    fclose(f);
    printf("R3_MOV v%s bytes=%ld fnv64=%016llx\n", argv[2], size, (unsigned long long)fnv64(data, (size_t)size));
    if (EnterMovies() != noErr)
        return 5;
    ref = NewHandle((long)sizeof rec);
    rec.data = data;
    rec.dataLength = (Size)size;
    memcpy(*ref, &rec, sizeof rec);
    e = NewMovieFromDataRef(&m, 0, NULL, ref, PointerDataHandlerSubType);
    DisposeHandle(ref);
    if (e != noErr || !(t = GetMovieIndTrack(m, 1)) || !(md = GetTrackMedia(t)) ||
        GetMediaTimeScale(md) != 8000 || GetMediaSampleCount(md) != 100)
        return 6;
    memset(data, 0x5A, (size_t)size); /* the movie owns its samples */
    free(data);
    h = NewEmptyHandle();
    e = GetMediaSample(md, h, 0, &bytes, 0, NULL, NULL, NULL, NULL, 0, &count, NULL);
    if (e != noErr || bytes != 200 || count != 100 || GetHandleSize(h) != 200)
        return 7;
    printf("R3_GETMEDIASAMPLE bytes=%ld samples=%ld pcm_fnv64=%016llx\n", (long)bytes, (long)count,
           (unsigned long long)fnv64((const unsigned char *)*h, 200));
    fflush(stdout);
    setenv("C10_AUDIO_REQUEST", argv[3], 1);
    setenv("C10_AUDIO_REPLY", argv[4], 1);
    HLock(h);
    rc = b06_hal_run((const unsigned char *)*h, 100u);
    HUnlock(h);
    printf("R3_HAL_RC=%d\n", rc);
    DisposeHandle(h);
    DisposeMovie(m);
    ExitMovies();
    if (rc == 0)
        printf("B11E_R3_FIFO_CHAIN_GUEST_OK\n");
    return rc;
}
