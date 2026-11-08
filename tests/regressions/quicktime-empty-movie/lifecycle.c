/* SPDX-License-Identifier: GPL-3.0-or-later */
#include <QuickTime/QuickTime.h>
#include <stdlib.h>
#include <stdio.h>
#include "allocator-api.h"

static unsigned checks, failures, live_allocations, allocation_calls;
static int fail_next_allocation;
#define CHECK(x) do { ++checks; if (!(x)) { ++failures; \
    printf("FAIL line %d: %s\n", __LINE__, #x); } } while (0)

void *d4rl_test_malloc(size_t size)
{
    void *result;
    ++allocation_calls;
    if (fail_next_allocation) { fail_next_allocation = 0; return NULL; }
    result = malloc(size);
    if (result) ++live_allocations;
    return result;
}
void d4rl_test_free(void *ptr)
{
    if (ptr) --live_allocations;
    free(ptr);
}
extern int d4rl_cpp_contract(void);
static void expect_error(OSErr expected)
{
    CHECK(GetMoviesError() == expected);
    CHECK(GetMoviesError() == 0); /* reads consume the current error */
}

int main(void)
{
    Movie a, b, extra;
    unsigned i, calls;
    CHECK(sizeof(SInt32) == 4 && sizeof(TimeScale) == 4 && sizeof(OSErr) == 2);
    CHECK(sizeof(Movie) == sizeof(void *));
    CHECK(d4rl_cpp_contract());
    ExitMovies();
    CHECK(NewMovie(0) == NULL);
    expect_error(-2020);
    CHECK(EnterMovies() == 0);
    CHECK(EnterMovies() == 0);
    a = NewMovie(0);
    b = NewMovie(0);
    CHECK(a && b && a != b);
    if (!a || !b) { ExitMovies(); return 1; }
    CHECK(*a && *b);
    CHECK(GetMovieTimeScale(a) == 600);
    CHECK(GetMovieTimeScale(b) == 600);
    SetMovieTimeScale(a, 44100);
    expect_error(0);
    CHECK(GetMovieTimeScale(a) == 44100);
    CHECK(GetMovieTimeScale(b) == 600);
    SetMovieTimeScale(b, (TimeScale)2147483647);
    CHECK(GetMovieTimeScale(b) == (TimeScale)2147483647);
    SetMovieTimeScale(a, 0);
    expect_error(-50);
    CHECK(GetMovieTimeScale(a) == 44100);
    SetMovieTimeScale(a, -1);
    expect_error(-50);
    CHECK(GetMovieTimeScale(a) == 44100);
    calls = allocation_calls;
    CHECK(NewMovie(1) == NULL);
    expect_error(-4);
    CHECK(NewMovie(-1) == NULL);
    expect_error(-4);
    CHECK(allocation_calls == calls); /* unsupported flags allocate nothing */
    CHECK(GetMovieTimeScale(NULL) == 0);
    expect_error(-2010);
    SetMovieTimeScale(NULL, 48000);
    expect_error(-2010);
    DisposeMovie(NULL);
    expect_error(-2010);
    fail_next_allocation = 1;
    CHECK(NewMovie(0) == NULL);
    expect_error(-108);
    CHECK(live_allocations == 2);
    DisposeMovie(a);
    expect_error(0);
    CHECK(live_allocations == 1);
    CHECK(GetMovieTimeScale(b) == (TimeScale)2147483647);
    for (i = 0; i < 1000; ++i) {
        Movie movie = NewMovie(0);
        CHECK(movie != NULL);
        if (!movie) break;
        CHECK(GetMovieTimeScale(movie) == 600);
        SetMovieTimeScale(movie, (TimeScale)(1000 + i));
        CHECK(GetMovieTimeScale(movie) == (TimeScale)(1000 + i));
        DisposeMovie(movie);
        CHECK(live_allocations == 1);
    }
    CHECK(EnterMovies() == 0); /* idempotent, not reference counted */
    CHECK(GetMovieTimeScale(b) == (TimeScale)2147483647);
    extra = NewMovie(0);
    CHECK(extra != NULL);
    CHECK(live_allocations == 2);
    ExitMovies(); /* cleanup the two remaining objects */
    expect_error(0);
    CHECK(live_allocations == 0);
    CHECK(NewMovie(0) == NULL);
    expect_error(-2020);
    CHECK(EnterMovies() == 0);
    a = NewMovie(0);
    CHECK(a != NULL);
    if (a) {
        CHECK(GetMovieTimeScale(a) == 600);
        DisposeMovie(a);
    }
    ExitMovies();
    ExitMovies(); /* repeated shutdown is harmless in this subset */
    CHECK(live_allocations == 0);
    printf("CHECKS=%u FAILURES=%u LIVE_ALLOCATIONS=%u\n",
           checks, failures, live_allocations);
    return failures ? 1 : 0;
}
