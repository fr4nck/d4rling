/* SPDX-License-Identifier: GPL-3.0-or-later
 * E3-B2: original MacMemory.cpp and real Darwin Handle allocation.
 * No test substitute for NewHandle or GetHandleSize.
 */
#define main e3b1_main
#include "quicktime-tracks/witness.c"
#undef main

#include <CarbonCore/MacMemory.h>
extern OSErr MemError(void);
extern void d4rl_qa_fail_next_realloc(void);


static int c2_main(void)
{
    static const struct trk mono[] = {
        {'s', 8000, 100, 1}
    };
    static const struct trk stereo[] = {
        {'s', 44100, 1000, 2}
    };
    static const struct trk mixed[] = {
        {'v', 30000, 10, 0},
        {'s', 44100, 1000, 2}
    };

    Movie m = NULL;
    Track t;
    Media md;
    Handle h, tiny;
    Size cap, tiny_cap;
    SInt32 bytes = -1, count = -1, index = -1;
    TimeValue sample_time = -1, duration = -1;
    SInt16 flags = -1;
    unsigned start_checks, start_failures;
    int exact_sizes;

    puts("D4RLING-E3B2-MACMEMORY-R1-ENTRY");

    if (e3b1_main() != 0)
        return 1;

    start_checks = checks;
    start_failures = failures;

#if defined(__APPLE__) && defined(__i386__)
    /* True Darwin Mach-O i386 ABI. */
    CHECK(sizeof(void *) == 4);
    CHECK(sizeof(Handle) == 4);
    CHECK(sizeof(Size) == 4);
    puts("C3_ABI=DARWIN_I386");
#elif defined(__linux__) && defined(__x86_64__)
    /* Linux native LP64 ABI, not the guest ABI. */
    CHECK(sizeof(void *) == 8);
    CHECK(sizeof(Handle) == 8);
    CHECK(sizeof(Size) == 8);
    puts("C3_ABI=LINUX_X64");
#else
#error Unsupported host or guest ABI for E3-B2-C3 witness
#endif
    CHECK(sizeof(SInt32) == 4);
    CHECK(sizeof(OSErr) == 2);

    CHECK(GetMediaSample((Media)0x10, NULL,
          0, NULL, 0, NULL, NULL, NULL,
          NULL, 1, NULL, NULL) == -2020);

    CHECK(EnterMovies() == noErr);

    h = NewHandle(64);
    if (!h || !*h) {
        puts("HANDLE_ALLOCATION=FAIL");
        return 10;
    }

    tiny = NewHandle(1);
    if (!tiny || !*tiny) {
        DisposeHandle(h);
        puts("TINY_HANDLE_ALLOCATION=FAIL");
        return 11;
    }

    cap = GetHandleSize(h);
    tiny_cap = GetHandleSize(tiny);

    printf("HANDLE_REQUESTED_64_REPORTED=%ld\n", (long)cap);
    printf("HANDLE_REQUESTED_1_REPORTED=%ld\n", (long)tiny_cap);

    CHECK(cap == 64);
    CHECK(tiny_cap == 1);


    /* Redimensionnement echoue : ne jamais perdre les donnees. */
    (*tiny)[0] = (char)0x5A;

    d4rl_qa_fail_next_realloc();
    SetHandleSize(tiny, 2);

    CHECK(MemError() == -108);
    CHECK(GetHandleSize(tiny) == 1);
    CHECK((unsigned char)(*tiny)[0] == 0x5A);

    /* Redimensionnement reussi : taille logique exacte. */
    SetHandleSize(tiny, 2);
    CHECK(MemError() == noErr);
    CHECK(GetHandleSize(tiny) == 2);
    CHECK((unsigned char)(*tiny)[0] == 0x5A);

    SetHandleSize(tiny, 1);
    CHECK(MemError() == noErr);
    CHECK(GetHandleSize(tiny) == 1);
    CHECK((unsigned char)(*tiny)[0] == 0x5A);

    exact_sizes = cap == 64 && tiny_cap == 1;

    if (exact_sizes)
        puts("HANDLE_LOGICAL_SIZE=EXACT");
    else
        puts("HANDLE_LOGICAL_SIZE=NONCONFORMANT");

    /*
     * Do not use the one-byte Handle for a two-byte sample
     * when its reported logical size is unreliable.
     */

    build(mono, 1);
    CHECK(open_buf(&m) == noErr && m != NULL);

    if (!m) {
        DisposeHandle(tiny);
        DisposeHandle(h);
        ExitMovies();
        return 12;
    }

    t = GetMovieIndTrack(m, 1);
    md = GetTrackMedia(t);
    CHECK(md != NULL);

    /* C3: a logical 1-byte Handle must grow to two bytes. */
    (*tiny)[0] = (char)0xA5;
    bytes = -77;
    count = -77;

    CHECK(GetMediaSample(md, tiny, 0, &bytes, 0,
          NULL, NULL, NULL, NULL, 1, &count, NULL) == noErr);

    CHECK(bytes == 2 && count == 1);
    CHECK(GetHandleSize(tiny) == 2);
    CHECK(memcmp(*tiny, pcm_ref, 2) == 0);


    memset(*h, 0xA5, 64);

    CHECK(GetMediaSample(md, h, 2,
          &bytes, 0, &sample_time, &duration,
          NULL, &index, 1, &count, &flags) == noErr);

    CHECK(bytes == 2 && count == 1);
    CHECK(sample_time == 0 && duration == 1);
    CHECK(index == 1 && flags == 0);
    CHECK(memcmp(*h, pcm_ref, 2) == 0);
    CHECK((unsigned char)(*h)[2] == 0xA5);

    memset(*h, 0xA5, 64);

    CHECK(GetMediaSample(md, h, 8,
          &bytes, 10, &sample_time, &duration,
          NULL, &index, 0, &count, &flags) == noErr);

    CHECK(bytes == 8 && count == 4);
    CHECK(sample_time == 10 && duration == 1);
    CHECK(memcmp(*h, pcm_ref + 20, 8) == 0);
    CHECK((unsigned char)(*h)[8] == 0xA5);

    memset(*h, 0xA5, 64);

    CHECK(GetMediaSample(md, h, 0,
          &bytes, 99, NULL, NULL,
          NULL, NULL, 1, &count, NULL) == noErr);

    CHECK(bytes == 2 && count == 1);
    CHECK(memcmp(*h, pcm_ref + 198, 2) == 0);

    memset(*h, 0xA5, 64);

    CHECK(GetMediaSample(md, h, 1,
          NULL, 0, NULL, NULL,
          NULL, NULL, 1, NULL, NULL) == -2027);

    CHECK((unsigned char)(*h)[0] == 0xA5);

    CHECK(GetMediaSample(md, h, 0,
          NULL, -1, NULL, NULL,
          NULL, NULL, 1, NULL, NULL) == -2032);

    CHECK(GetMediaSample(md, h, 0,
          NULL, 100, NULL, NULL,
          NULL, NULL, 1, NULL, NULL) == -2032);

    DisposeMovie(m);

    CHECK(GetMediaSample(md, h, 2,
          NULL, 0, NULL, NULL,
          NULL, NULL, 1, NULL, NULL) == -2008);

    build(mixed, 2);
    CHECK(open_buf(&m) == noErr && m != NULL);

    if (!m) {
        DisposeHandle(tiny);
        DisposeHandle(h);
        ExitMovies();
        return 13;
    }

    md = GetTrackMedia(GetMovieIndTrack(m, 1));

    CHECK(GetMediaSample(md, h, 4,
          NULL, 0, NULL, NULL,
          NULL, NULL, 1, NULL, NULL) == -4);

    md = GetTrackMedia(GetMovieIndTrack(m, 2));

    CHECK(GetMediaSample(md, h, 4,
          &bytes, 0, NULL, NULL,
          NULL, NULL, 1, &count, NULL) == noErr);

    CHECK(bytes == 4 && count == 1);
    CHECK(memcmp(*h, pcm_ref, 4) == 0);

    DisposeMovie(m);

    build(stereo, 1);
    CHECK(open_buf(&m) == noErr && m != NULL);

    if (!m) {
        DisposeHandle(tiny);
        DisposeHandle(h);
        ExitMovies();
        return 14;
    }

    md = GetTrackMedia(GetMovieIndTrack(m, 1));

    CHECK(GetMediaSample(md, h, 4,
          &bytes, 0, NULL, NULL,
          NULL, NULL, 1, &count, NULL) == noErr);

    CHECK(bytes == 4 && count == 1);
    CHECK(memcmp(*h, pcm_ref, 4) == 0);

    DisposeMovie(m);
    DisposeHandle(tiny);
    DisposeHandle(h);
    ExitMovies();

    printf("QA2_PCM_CHECKS=%u QA2_PCM_FAILURES=%u\n",
           checks - start_checks, failures - start_failures);

    if (failures != start_failures) {
        puts("D4RLING-E3B2-MACMEMORY-PCM-FAIL");
        return 2;
    }

    puts("D4RLING-E3B2-MACMEMORY-PCM-OK");
    return 0;
}


int main(void)
{
    static const struct trk mono[] = {
        {'s', 8000, 100, 1}
    };
    Movie m = NULL;
    Media md;
    Handle empty, tiny;
    Ptr before_ptr;
    SInt32 bytes, n;
    unsigned before_checks, before_failures;

    puts("D4RLING-E3B2-C3-ENTRY");

    if (c2_main() != 0)
        return 1;

    before_checks = checks;
    before_failures = failures;

    CHECK(EnterMovies() == noErr);

    build(mono, 1);
    CHECK(open_buf(&m) == noErr && m != NULL);

    if (!m)
        return 2;

    md = GetTrackMedia(GetMovieIndTrack(m, 1));
    CHECK(md != NULL);

    empty = NewEmptyHandle();
    CHECK(empty != NULL);

    if (!empty)
        return 3;

    CHECK(*empty == NULL);
    CHECK(GetHandleSize(empty) == 0);

    bytes = -1;
    n = -1;

    CHECK(GetMediaSample(md, empty, 0, &bytes,
          0, NULL, NULL, NULL, NULL, 1, &n, NULL) == noErr);

    CHECK(bytes == 2 && n == 1);
    CHECK(GetHandleSize(empty) == 2);
    CHECK(*empty != NULL);
    CHECK(memcmp(*empty, pcm_ref, 2) == 0);

    /* Let QuickTime choose the count from the whole media. */
    CHECK(GetMediaSample(md, empty, 0, &bytes,
          0, NULL, NULL, NULL, NULL, 0, &n, NULL) == noErr);

    CHECK(bytes == 200 && n == 100);
    CHECK(GetHandleSize(empty) >= 200);
    CHECK(memcmp(*empty, pcm_ref, 200) == 0);

    /* Bound the returned bytes to two stereo-sized frames,
     * or four bytes in this mono fixture. */
    CHECK(GetMediaSample(md, empty, 4, &bytes,
          10, NULL, NULL, NULL, NULL, 0, &n, NULL) == noErr);

    CHECK(bytes == 4 && n == 2);
    CHECK(memcmp(*empty, pcm_ref + 20, 4) == 0);

    tiny = NewHandle(1);
    CHECK(tiny != NULL);

    if (!tiny) {
        DisposeHandle(empty);
        DisposeMovie(m);
        ExitMovies();
        return 4;
    }

    CHECK(GetHandleSize(tiny) == 1);

    (*tiny)[0] = (char)0xA5;
    before_ptr = *tiny;

    /* Inject a genuine resizing failure in the candidate MM. */
    d4rl_qa_fail_next_realloc();

    bytes = -77;
    n = -77;

    CHECK(GetMediaSample(md, tiny, 0, &bytes,
          0, NULL, NULL, NULL, NULL, 1, &n, NULL) == -108);

    CHECK(bytes == -77 && n == -77);
    CHECK(GetHandleSize(tiny) == 1);
    CHECK(*tiny == before_ptr);
    CHECK((unsigned char)(*tiny)[0] == 0xA5);

    /* Retry without injected failure. */
    CHECK(GetMediaSample(md, tiny, 0, &bytes,
          0, NULL, NULL, NULL, NULL, 1, &n, NULL) == noErr);

    CHECK(bytes == 2 && n == 1);
    CHECK(GetHandleSize(tiny) == 2);
    CHECK(memcmp(*tiny, pcm_ref, 2) == 0);

    /* A maximum size smaller than one PCM sample is refused. */
    bytes = -19;
    CHECK(GetMediaSample(md, tiny, 1, &bytes,
          0, NULL, NULL, NULL, NULL, 1, NULL, NULL) == -2027);
    CHECK(bytes == -19);

    CHECK(GetMediaSample(md, tiny, -1, NULL,
          0, NULL, NULL, NULL, NULL, 1, NULL, NULL) == -50);

    CHECK(GetMediaSample(md, NULL, 0, NULL,
          0, NULL, NULL, NULL, NULL, 1, NULL, NULL) == -50);

    DisposeHandle(tiny);
    DisposeHandle(empty);
    DisposeMovie(m);
    ExitMovies();

    printf("C3_CHECKS=%u C3_FAILURES=%u\n",
           checks - before_checks,
           failures - before_failures);

    if (failures == before_failures &&
        checks - before_checks >= 25) {
        puts("D4RLING-E3B2-C3-OK");
        return 0;
    }

    puts("D4RLING-E3B2-C3-FAIL");
    return 5;
}
