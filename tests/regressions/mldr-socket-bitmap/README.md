# mldr RPC socket bitmap regression

This focused host-only test exercises the actual `socket_bitmap_get` and
`socket_bitmap_put` function bodies extracted from
`src/startup/mldr/mldr.c`. It never runs the Darling loader, launches guests,
installs packages, downloads dependencies, or changes a Darling prefix.

## Run

From the root of an existing checkout:

```sh
ruby tests/regressions/mldr-socket-bitmap/run.rb
```

Requires Ruby and Clang with AddressSanitizer and UndefinedBehaviorSanitizer
support. The runner creates a temporary C harness, compiles and executes it
under ASan+UBSan, and deletes the temporary files on exit.

Expected: `PASS: bitmap shrink keeps live slots and frees cleanly`.

Covered: preserve 16 live slots after releasing the upper byte; do not hand
out the same live descriptor twice; release all storage when the final slot
is freed; and regrow the bitmap afterwards.

## Source and provenance

Adapted from [VibeDarling/darling PR #1189](https://github.com/VibeDarling/darling/pull/1189)
and its `tests/mldr-socket-bitmap-shrink.rb` test (Git blob
`c4de0d32f03d1673314abbdccb4a7be4dd7da0a4`). The underlying fix
originated with lucannez64 (Kalah) in
[darling-lol](https://github.com/lucannez64/darling-lol),
commit `a96cdc6`. The regression extractor was adapted because this fork's
pinned `mldr.c` has no `__mldr_socket_bitmap_prefork` anchor used by the
neighbor's newer source layout. The original Darling GPL notice remains in
`mldr.c`; this regression script follows GPL-3.0-or-later.

On 2026-10-28 an independent isolated C-copy reproduction (not a checkout
of this repository) was run under Clang ASan+UBSan: the baseline failed at
`bitmap.bit_length == 16` and the corrected copy passed. **The regression
against the complete committed production source has NOT YET BEEN EXECUTED
in this GitHub-only integration.** Run it on an existing checkout before
marking the PR ready. No proof of resolving the independent Darling RPC
`-111` runtime failure is claimed.

The neighbor patch's remaining potential unsigned-index underflow on
invalid socket values is not addressed by this bounded fix.
