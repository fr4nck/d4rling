# CoreMIDI virtual — portable test

Run from any directory in the repo:

    sh tests/regressions/coremidi-virtual/run.sh

Set CC=gcc to select GCC. The runner compiles the actual MIDIVirtual.c with a minimal CoreFoundation type shim. It does not test other Darling components or Mach-O exports.
