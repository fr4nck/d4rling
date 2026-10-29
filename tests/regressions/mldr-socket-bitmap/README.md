# mldr RPC socket bitmap — deterministic regression and qualification

## Purpose and scope

This directory tests the **actual bitmap type and functions extracted verbatim** from
`src/startup/mldr/mldr.c`. It does not execute a full `mldr`, a Darling guest,
or RPC against `darlingserver`.

The fix in [PR #6](https://github.com/fr4nck/d4rling/pull/6) is a bounded port
of [VibeDarling/darling #1189](https://github.com/VibeDarling/darling/pull/1189)
(original credit: lucannez64/Kalah, `darling-lol` `a96cdc6`).

- **Live-bit condition:** do not shrink through an occupied descriptor bit.
- **Zero-sized storage:** call `free` and set `bits = NULL`, avoiding
  implementation-dependent `realloc(ptr, 0)` behavior.

The separate historical `BAD SEND STATUS: -111` (Linux `ECONNREFUSED`)
is **not** a demonstrated consequence of either bitmap bug.

## Execute without downloading or installing anything

From an existing checkout of the PR's source, with pre-existing Python 3 and
Clang + ASan/UBSan:

```sh
python3 tests/regressions/mldr-socket-bitmap/run.py --expect-blob 2c05caaae9c13882cbc5d07fd3f3e4ebdee0687c
```

Optional, if Ruby is already installed:

```sh
ruby tests/regressions/mldr-socket-bitmap/run.rb
```

A checked-out branch is **not** required for `run.py` if passing
`--source /existing/pinned/mldr.c`; however, the runner and
`probe.c.in` must be present together in a private directory. The
`--expect-blob` flag verifies the *Git blob SHA-1* of the C source before
compilation; it does **not** download, install, checkout, or rewrite the
repository.

These runners create short-lived C probes under the system temporary
directory, compile only those probes, and leave actual build trees, native
loader executables, installations, and Darling prefixes unchanged. The
Python runner prefers an already-installed `clang-19`, then `clang`; Ruby
uses `CLANG` if set, else `clang`. Missing tools are a **BLOCKED** gate,
not permission to install.

Expected Python markers:

```text
SOURCE_GIT_BLOB=2c05caaae9c13882cbc5d07fd3f3e4ebdee0687c
COMPILE=PASS
PASS: deterministic mldr bitmap regression (120000 operations, ASan+UBSan)
TEST_EXIT=0
MLDR_PR6_DETERMINISTIC=PASS
```

The deterministic probe covers:

1. The original 24-allocated / eight-upper-freed scenario, preserving 16
   occupied slots and refusing to reissue them.
2. Explicit `bits == NULL` and `bit_length == 0` on complete release,
   followed by safe regrowth.
3. Bitmap-width boundaries 1, 7, 8, 9, 15, 16, 17, 23, 24, 25, 31,
   32, 33 and non-LIFO release orders.
4. 120,000 fixed-seed allocation/release operations against an independent
   live-descriptor model; checks `next_index`, live bitmap bits, logical
   length, duplicate allocation and zero-length storage.
5. ASan + UBSan on host-compiled *production function bodies*.

The runner is intentionally serial: the host's `pthread_mutex` is present
but no concurrent thread stress is claimed. Failure injection for
`realloc` and invalid `socket_bitmap_put` arguments is not included.
The pre-existing unsigned-index underflow on invalid socket values is
**outside PR #6's repair** and should be addressed in a separate reviewed
change, not silently expanded here.

## Three distinct evidence levels

**(A) Isolated/copy and source-extraction tests.** A standalone host-copy
test was reported to pass with sanitizer instrumentation; PR6B and
PR6L-R2 report 5700X checks against pinned production source bodies,
with old-source failure and patched-source success. PR6L-R2 extracted the
official Ruby test's C body but did not actually execute Ruby. The new
120,000-step test and two independent negative-control mutations were
executed in an isolated host workspace outside the user's 5700X. **A
new 5700X run of these newly versioned files is still pending.**

**(B) Built native source and linker tests.** PR6C and PR6D report that
the patched `mldr` ELF64 and `mldr32` ELF32 compile/link succeeded on
5700X with existing objects, without running Ninja, modifying builds,
or contacting the server. Those are genuine loader binaries, **not**
ASan-instrumented full-loader proofs.

**(C) Guest runtime.** PR6H reports a previously passing i386 Carbon
Mach-O guest run with corrected `mldr` and `mldr32` overmounted only
inside a disposable private mount namespace, passing NORMAL and BYPASS
(2/2) and host postflight integrity. This does **not** instrument
`socket_bitmap_put` calls or prove correction of a `-111` failure.
PR6I–PR6K identified historical JACK `explicit_checkin` errors but
also found the historical pilots **BLOCKED** with no qualified
old-vs-patched comparator. Do not characterize the `-111` issue as fixed.

Raw 5700X reports remain on the user's machine. References and
provenance were posted as dated comments on PR #6. No invented CI result,
Ruby-runner result, guest-RPC comparison, or merge authorization is
implied by this README.

## Merge gate

Keep PR #6 **draft** until (i) the user has run/inspected the current
pinned deterministic regression in an existing complete checkout, (ii)
the regression output and source hashes are added to the PR with provenance,
(iii) the existing isolated ELF32/ELF64 and guest runtime evidence is
reviewed, and (iv) a reviewer explicitly approves the bounded patch.
A reproduced guest RPC `-111` regression is **not** a prerequisite to
the bounded bitmap fix unless claimed as fixed — it must never be presented
as a success without a controlled comparison.

For a protected, no-installation read-only run on the 5700X, use
`verify-5700x.sh` from this directory. It refuses missing pinned local
objects instead of fetching or checking out anything.
