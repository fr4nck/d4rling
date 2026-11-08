/* SPDX-License-Identifier: GPL-3.0-or-later */
#include <QuickTime/QuickTime.h>
#include <type_traits>
static_assert(sizeof(SInt32) == 4, "flags must be 32 bits");
static_assert(sizeof(TimeScale) == 4 && TimeScale(-1) < 0, "signed scale");
static_assert(sizeof(OSErr) == 2, "OSErr must be 16 bits");
static_assert(std::is_same<decltype(&EnterMovies), OSErr (*)(void)>::value, "EnterMovies");
static_assert(std::is_same<decltype(&ExitMovies), void (*)(void)>::value, "ExitMovies");
static_assert(std::is_same<decltype(&GetMoviesError), OSErr (*)(void)>::value, "GetMoviesError");
static_assert(std::is_same<decltype(&NewMovie), Movie (*)(SInt32)>::value, "NewMovie");
static_assert(std::is_same<decltype(&DisposeMovie), void (*)(Movie)>::value, "DisposeMovie");
static_assert(std::is_same<decltype(&GetMovieTimeScale), TimeScale (*)(Movie)>::value, "GetMovieTimeScale");
static_assert(std::is_same<decltype(&SetMovieTimeScale), void (*)(Movie, TimeScale)>::value, "SetMovieTimeScale");
/* Link all seven C symbols from a C++ translation unit. */
static OSErr (*enter_fn)(void) = &EnterMovies;
static void (*exit_fn)(void) = &ExitMovies;
static OSErr (*error_fn)(void) = &GetMoviesError;
static Movie (*new_fn)(SInt32) = &NewMovie;
static void (*dispose_fn)(Movie) = &DisposeMovie;
static TimeScale (*get_fn)(Movie) = &GetMovieTimeScale;
static void (*set_fn)(Movie, TimeScale) = &SetMovieTimeScale;
extern "C" int d4rl_cpp_contract(void)
{
    return enter_fn && exit_fn && error_fn && new_fn && dispose_fn && get_fn && set_fn;
}
