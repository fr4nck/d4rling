# BSD i386 R4-B — 17 synthetic cases, local reproduction

Date: 2026-11-10. Base branch: master, observed HEAD `afed46219191cb0d93cdb2e09f92e0413c14cfeb`.

## Execution

An independent Python 3.13.5 Linux container ran a **local reconstruction** of the probe logic and the 17 synthetic unittest cases represented by `reproduction/fixtures/bsd-i386-r4-b-readonly.py` and `reproduction/fixtures/test_bsd_i386_r4_b_readonly.py`.

Command: `python3 -m unittest discover -s . -p 'test_bsd_i386_r4_b_readonly.py' -v`.

Observed result: `Ran 17 tests in 0.001s — OK` (17 PASS, 0 FAIL, 0 ERROR). Coverage includes thin i386 (both endian variants), FAT (both endian variants, padding), PIE flag, malformed load commands, truncated segment, invalid command table, missing/duplicate i386 FAT slices, out-of-bounds slices and slices overlapping the FAT architecture table.

## Qualification limits

**This is not an execution of the byte-identical GitHub source files.** The local files were reconstructed from the GitHub connector output and earlier local fixture copies; they have no byte-for-byte checksum match to the current repository files. The complete GitHub probe CLI (file validation, stderr handling and SHA-256 reporting) was not executed. Accordingly, status for the canonical 17-test suite remains **NOT YET VERIFIED BYTE-FOR-BYTE**.

No real historical i386 executable was tested. No loader or guest code was executed. No proof of effective `mmap` address, loader slide, audio output or Logic Studio 8 compatibility is implied. No changes to `vm.mmap_min_addr` or production loader were made.

## Next gate

Run the canonical GitHub test file and probe byte-for-byte on an available runner, record SHA-256, Python version and full unittest output, then investigate the 50 AUD-R3 low-mapping failures without assuming the logged unslid `vmaddr` is the attempted effective address.
