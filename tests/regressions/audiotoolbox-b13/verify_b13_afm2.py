#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""ATB-FIX3 positive oracle: verdict on the b13-afm2 outputs of one architecture, plus the
comparison of both architectures.
  verify_b13_afm2.py I386_DIR X86_64_DIR   (each holds tables.log lookup.log open.log)

Expectations are fixed here BEFORE any run of the FIX3 candidate. Their sources, independent
of the candidate's output:
  SRC  src/CoreAudio/AFAVFormatComponent/AudioFileFormats.cpp: the 11 registered components and
       the extensions, UTIs and MIME types each one declares (the manager only has to pass them on);
  SRC  src/CoreAudio/AudioToolbox/AudioFile.cpp: AudioFileOpenURL tries the hint, then the types of
       the (lower-case) extension, then the readable types whose component recognizes the first
       64 KiB, in numeric order; it returns the status of the last component tried, or 'typ?'
       when there is no candidate at all; AFAVFormat answers 'dta?' when FFmpeg cannot open the file;
  ORACLE  b13-oracle.json: 88 200 frames in the demo files, 35 273 available in bad-trunc.wav;
  REF  unpatched reference already published (B13-INT, results-b13-integration.json):
       the probing of bad-garbage.wav matches no component (x86_64 'typ?' with no extension type).
Every check must hold in BOTH architectures, and every b13-afm2 line must be identical in both."""
import re, sys
from pathlib import Path

DESC = {  # AudioFileFormats.cpp, transcribed: type -> (extensions, utis, mimes)
    'WAVE': (['wav', 'wave'], ['com.microsoft.waveform-audio', 'public.audio', 'public.data'], ['audio/wav', 'audio/x-wav', 'audio/vnd.wave']),
    'AIFF': (['aif', 'aiff'], ['public.aiff-audio', 'public.audio', 'public.data'], ['audio/aiff', 'audio/x-aiff']),
    'AIFC': (['aifc', 'cdda'], ['public.aifc-audio', 'public.audio', 'public.data'], ['audio/aiff', 'audio/x-aiff']),
    'caff': (['caf'], ['com.apple.coreaudio-format', 'public.audio', 'public.data'], ['audio/x-caf']),
    'NeXT': (['au', 'snd'], ['public.ulaw-audio', 'public.audio', 'public.data'], ['audio/basic']),
    'MPG3': (['mp3'], ['public.mp3', 'public.audio', 'public.data'], ['audio/mpeg', 'audio/mp3']),
    'adts': (['aac', 'adts'], ['public.aac-audio', 'public.audio', 'public.data'], ['audio/aac', 'audio/x-aac']),
    'm4af': (['m4a', 'm4r'], ['com.apple.m4a-audio', 'public.audio', 'public.data'], ['audio/mp4', 'audio/x-m4a']),
    'mp4f': (['mp4'], ['public.mpeg-4-audio', 'public.audio', 'public.data'], ['audio/mp4']),
    'flac': (['flac'], ['org.xiph.flac', 'public.audio', 'public.data'], ['audio/flac', 'audio/x-flac']),
    'ac-3': (['ac3'], ['public.ac3-audio', 'public.audio', 'public.data'], ['audio/ac3']),
}
ALL = [sorted({v for d in DESC.values() for v in d[i]}) for i in range(3)]
assert (len(ALL[0]), len(ALL[1]), len(ALL[2])) == (17, 13, 16)
LOOKUP = {
    'types_for_extension:wav': ['WAVE'], 'types_for_extension:wave': ['WAVE'], 'types_for_extension:aif': ['AIFF'],
    'types_for_extension:aiff': ['AIFF'], 'types_for_extension:aifc': ['AIFC'], 'types_for_extension:caf': ['caff'],
    'types_for_extension:zzzq': [],
    'types_for_uti:com.microsoft.waveform-audio': ['WAVE'], 'types_for_uti:public.aiff-audio': ['AIFF'],
    'types_for_uti:public.aifc-audio': ['AIFC'], 'types_for_uti:org.example.none': [],
    'types_for_mime:audio/x-wav': ['WAVE'], 'types_for_mime:audio/aiff': ['AIFC', 'AIFF'], 'types_for_mime:audio/x-none': [],
}
N, TRUNC = 88200, 35273
OPEN = {  # key: (status, file_format, packets)
    'wav_nohint': ('0', 'WAVE', N), 'wav_hint_WAVE': ('0', 'WAVE', N),
    'wav_hint_AIFF': ('0', 'WAVE', N),            # AIFF refuses RIFF data, the extension gives WAVE
    'aiff_nohint': ('0', 'AIFF', N),              # the extension decides (AIFF and AIFC share FFmpeg's demuxer)
    'aiff_hint_AIFF': ('0', 'AIFF', N), 'aiff_hint_AIFC': ('0', 'AIFC', N),   # an explicit hint is tried first
    'aif_nohint': ('0', 'AIFF', N),
    'aifc_nohint': ('0', 'AIFC', N), 'aifc_hint_AIFC': ('0', 'AIFC', N), 'aifc_hint_AIFF': ('0', 'AIFF', N),
    'garbage_wav_nohint': ('dta?', '-', -1), 'garbage_wav_hint_WAVE': ('dta?', '-', -1),
    'empty_wav_nohint': ('dta?', '-', -1),        # the extension gives WAVE, which cannot open an empty file
    'trunc_wav_nohint': ('0', 'WAVE', TRUNC),
    'garbage_zzzq_nohint': ('typ?', '-', -1),     # no extension type, no component recognizes the data
    'empty_zzzq_nohint': ('typ?', '-', -1),       # no candidate at all
}

def load(d):
    r = {}
    for f in ('tables.log', 'lookup.log', 'open.log'):
        p = Path(d) / f
        for line in (p.read_text(errors='replace').splitlines() if p.exists() else []):
            m = re.match(r'B13AFM2 (open )?(\S+) (.*)$', line)
            if m:
                r[m.group(2)] = dict(x.split('=', 1) for x in m.group(3).split(' ') if '=' in x)
    return r

def lines(d):
    return [l for f in ('tables.log', 'lookup.log', 'open.log') if (Path(d) / f).exists()
            for l in (Path(d) / f).read_text(errors='replace').splitlines() if l.startswith('B13AFM2 ')]

checks = []
def chk(name, ok, detail=''):
    checks.append(bool(ok))
    print(f"AFM2 {name} {'PASS' if ok else 'FAIL'} {detail}")

def vals(e): return [v for v in e.get('values', '').split(',') if v] if e else None

for arch, d in (('i386', sys.argv[1]), ('x86_64', sys.argv[2])):
    r = load(d)
    for t in ('WAVE', 'AIFF', 'AIFC', 'caff'):
        for i, k in enumerate(('extensions', 'utis', 'mimes')):
            e = r.get(f'{k}_for_{t}')
            chk(f'{arch}_{k}_for_{t}', e and e['status'] == '0' and sorted(vals(e)) == sorted(DESC[t][i]), str(e))
    for i, k in enumerate(('all_extensions', 'all_utis', 'all_mimes')):
        e = r.get(k)
        chk(f'{arch}_{k}', e and e['status'] == '0' and sorted(vals(e)) == ALL[i], f"count={e and e.get('count')}")
    e = r.get('readable_types')
    chk(f'{arch}_readable_types', e and e['status'] == '0' and sorted(vals(e)) == sorted(DESC), str(e))
    e = r.get('component_wave_extensions')
    chk(f'{arch}_component_wave_extensions', e and e['status'] == '0' and sorted(vals(e)) == DESC['WAVE'][0], str(e))
    for k, want in LOOKUP.items():
        e = r.get(k)
        chk(f'{arch}_{k}', e and e['status'] == '0' and sorted(vals(e)) == sorted(want), str(e))
    for k, (st, ff, pk) in OPEN.items():
        e = r.get(k)
        ok = e and e['status'] == st and e['file_format'] == ff and int(e['packets']) == pk and e['handle'] == ('set' if st == '0' else 'null')
        chk(f'{arch}_open_{k}', ok, str(e))
li, lx = lines(sys.argv[1]), lines(sys.argv[2])
diff = [(a, b) for a, b in zip(li, lx) if a != b]
chk('i386_equals_x86_64', len(li) == len(lx) and li and not diff, f"lines={len(li)}/{len(lx)} differing={len(diff)} {diff[:3]}")
print(f"AFM2_SUMMARY checks={len(checks)} failures={checks.count(False)} verdict={'FIX3_POSITIVE_PASS' if all(checks) else 'FIX3_POSITIVE_FAIL'}")
sys.exit(0 if all(checks) else 1)
