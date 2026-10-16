# CoreMIDI -> ALSA native sequencer loopback (experimental)

Run from the repository checkout on Linux:

```sh
sh tests/regressions/coremidi-alsa/run.sh
CC=gcc sh tests/regressions/coremidi-alsa/run.sh
```

Prerequisites: a C compiler, pkg-config, genuine ALSA development headers and
libasound. The runner uses the actual `MIDIVirtual.c` and `MIDIAlsaBridge.c`
sources, compiled **natively** outside the Darling framework. It creates an
ALSA input client, locates its endpoint via public CoreMIDI enumeration, sends
Note On/Off (channel 1, note 60), and checks their delivery and byte values.

Output markers:
- `ALSA_COMPILE_PASS`: the native build and link completed.
- `ALSA_RUNTIME_PASS`: ALSA delivered Note On and Note Off.
- `ALSA_COMPILE_SKIP`: libasound development files or pkg-config missing.
- `ALSA_RUNTIME_SKIP`: /dev/snd/seq missing (exit 77).
- `ALSA_RUNTIME_FAIL`: receiver creation, discovery, delivery or validation failure.

An exit status of 77 means **not qualified**, not a passing ALSA runtime test.
This test does not prove ELF/Mach-O wrapping, physical USB MIDI, MIDI input
support, timing accuracy, concurrency safety, or Logic Studio compatibility.
