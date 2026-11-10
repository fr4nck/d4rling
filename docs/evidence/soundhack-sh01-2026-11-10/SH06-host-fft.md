# SoundHack SH06 — original FFT DSP on a Linux host (10 November 2026)

**Qualification: HOST DSP PASS only.** This is not SoundHack SH-LOAD, SH-GUI, SH-FILE, SH-DSP (in guest), SH-AUDIO or Logic Studio 8 compatibility.

## Source and integrity

- Author: Tom Erbe. Official source snapshot: [tomerbe/SoundHack@df6f0bc](https://github.com/tomerbe/SoundHack/tree/df6f0bc89243b93573b391afa5ab371cce56ac95); MIT license.
- Original source used unaltered: Math/FFT.c Git blob **b132ab450a71b451f5ae9e5649c98a6a41c9f9e9**; Math/FFT.h blob **f31c2d41526d3768ad7cb0f10993847d2bd6ae84**.
- Both original files were obtained into a private temporary test folder via connected GitHub and independently verified by git hash-object. No Apple SDK, SoundHack executable, third-party source file or media is committed to D4rling.
- New GPL-3.0-or-later test files: reproduction/fixtures/soundhack-i386/fft_host_probe.py and test_fft_host_probe.py.
- Execution was inside an isolated Linux x86_64 tools container, not the user's 5700X. No installer, audio device or D4rling guest was used.

## What was actually executed

The probe compiles **the unchanged original upstream FFT.c**, including FFT and RealFFT, as a private host shared object using an already available C compiler. The only added test-time C companion defines the Pi and twoPi globals normally provided by SoundHack. Python ctypes calls the compiled functions.

The independent oracle is a double-precision **O(N²) discrete Fourier transform**. The SoundHack forward sign convention is positive; RealFFT puts DC/Nyquist into the first two floats. The corpus checks impulse and mixed inputs at 2, 4, 8, 16, 32 and 64 complex FFT points, with real samples twice that length. It compares each forward spectrum to the direct DFT and each inverse result to the input.

A separate **128-sample two-tone processing** check (bins 5 and 19) uses the original RealFFT to zero bin 19, inverts the transform and compares the output to the bin-5-only target. This qualifies original host DSP numerical processing, not audio-file I/O.

## Results actually observed

| Observation | GCC 14.2 (cc) | Clang 17 |
|---|---:|---:|
| Real upstream FFT / RealFFT corpus | 24/24 PASS | 24/24 PASS |
| Max forward spectrum absolute error | 5.7248229e-6 | 5.7248229e-6 |
| Max inverse reconstruction absolute error | 6.3287764e-7 | 6.3287764e-7 |
| Two-tone notch output absolute error | 2.5791964e-7 | 2.5791964e-7 |
| Spectral processing check | PASS | PASS |

Limits: **1e-4** forward absolute error, **2e-5** inverse/processed error. Executed on Python **3.13.5**, GCC **14.2.0**, Clang **17.0.0**; host long is 64 bits. Only these bounded numerical inputs and toolchains were checked.

- Python unittest suite with pinned original Math directory available: **13 PASS, 0 FAIL**. It includes wrong-sign and removed-inverse-normalization mutants applied to isolated copies of the true upstream code, plus no-op, NaN, compile failure, missing symbol, compiler absence and hash-mismatch negatives.
- Same unittest suite without the external Math directory: **10 PASS, 3 SKIP**, no fabricated positive source test. Real-source cases require SOUNDHACK_MATH_DIR.
- All mutants were rejected. Missing or unqualified input yields INCONCLUSIVE; incorrect numerical output yields HOST_DSP_FAIL.
- Python py_compile succeeded for both new files. GitHub Actions was not used.

## Reproduction — no implicit download

From the D4rling checkout root, with a separately authorized **unchanged** SoundHack source tree already available at the path used in these examples:

    SOUNDHACK_MATH_DIR=/authorized/path/SoundHack/Math \
      python3 -m unittest discover -s reproduction/fixtures/soundhack-i386 -p 'test_fft_host_probe.py' -v
    python3 reproduction/fixtures/soundhack-i386/fft_host_probe.py \
      --source-dir /authorized/path/SoundHack/Math

The runner pins both upstream Git blobs and creates/removes only a private temporary build area. It never downloads code, modifies an installation or starts an application. Exit **0** = bounded numerical HOST_DSP_PASS; **2** = HOST_DSP_FAIL; **3** = INCONCLUSIVE. JSON contains the full case breakdown.

## Boundaries and next gate

This is **not** a Darwin i386 ABI test; the host's long is 64-bit. Neither execution of SoundHack under D4rling, application SH-DSP, an audio signal at an output device, QuickTime, GUI nor Logic's engine is validated. The original SoundHack 0.896 Universal Binary has not been acquired: the official UCSD archive endpoint remains unavailable due to DNS failure in this isolated test container.

The CarbonCore startup blockers discovered in [SH05](SH05-startup-gestalt.md) remain pending the owning thread's typed fix and tests: missing Gestalt Carbon selector ('cbon') and system-version ('sysv') fallthrough. There is **no** CarbonCore production change in SH06. The next SoundHack app step is an import/ordinal audit of the authentic 0.896 i386 binary when it becomes accessible, followed by coherent D4rling guest loading and GUI checks.
