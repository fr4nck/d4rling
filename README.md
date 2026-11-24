# QuickTime checkpoint - 2026-11-24

Independent source archive, not an integration branch.

QT13: qualified i386 reference for MOV metadata, PCM,
movie lifecycle, timescale, segments and seek.

QT16: experimental file backend. Public file API blocked
by Carbon FSSpec support. Incorrect pointer type must
be corrected before qualification.

The source-base directory preserves the intermediate
sources. Apply QT13 or QT16 cumulative patches to this
base independently, never QT16 on top of QT13.

Test templates ending in .in contain path placeholders.
Build reconstruction has not been replayed from this archive.
See qualification.json for missing files and source hashes.

CoreAudio playback remains blocked. Native PulseAudio
i386 connection has passed.

No compiled binaries, private runtime dependencies or
raw logs are published here.
