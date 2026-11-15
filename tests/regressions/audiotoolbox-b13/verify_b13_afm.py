#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""B13 defect 3: verdict from the b13-afm outputs of both architectures.
  verify_b13_afm.py I386_DIR X86_64_DIR   (each holds component.log tables.log ext-wav.log ext-zzzq.log open.log)
Expectations fixed before the runs (hypothesis from the source, SRC/HYP):
  - i386: sizeof(CFArrayRef) == 4, the size left by AudioFileFormatManager is right; tables filled.
  - x86_64: the WAVE component refuses size 4 ('!siz') and answers sizeof(CFArrayRef) == 8
    -> the manager gets no extensions/UTIs/MIME types; extension lookups find nothing.
  - negative reference in both: an unknown extension ('zzzq') maps to no type; ReadableTypes
    is the same list in both architectures (the database itself is built)."""
import re, sys
from pathlib import Path

def load(d):
    r = {}
    for f in sorted(Path(d).glob('*.log')):
        for line in f.read_text(errors='replace').splitlines():
            m = re.match(r'B13AFM (\S+?)(?:=(\S+))?(?: (.*))?$', line)
            if not m:
                continue
            k, v, rest = m.groups()
            if k in ('open', 'types_for_extension'):
                kv = dict(x.split('=', 1) for x in (rest or '').split() if '=' in x)
                key = (k + ':' + (rest.split()[0] if k == 'open' else kv['ext']))
                r[key] = kv
            elif v is not None and rest is None:
                r[k] = {'value': v}
            else:
                kv = dict(x.split('=', 1) for x in (rest or '').split(' ') if '=' in x)
                if v is not None:
                    kv['value'] = v
                r[k] = kv
    return r

i, x = load(sys.argv[1]), load(sys.argv[2])
checks = []
def chk(name, ok, detail=''):
    checks.append((name, bool(ok)))
    print(f"AFM {name} {'PASS' if ok else 'FAIL'} {detail}")

g = lambda r, k, f='status': r.get(k, {}).get(f)
cnt = lambda r, k: int(r.get(k, {}).get('count', '-1'))
chk('i386_sizeof_cfarrayref_4', g(i, 'sizeof_cfarrayref', 'value') == '4')
chk('x86_64_sizeof_cfarrayref_8', g(x, 'sizeof_cfarrayref', 'value') == '8')
for a, r in (('i386', i), ('x86_64', x)):
    chk(f'{a}_control_filetypename', g(r, 'control_filetypename') == '0', str(r.get('control_filetypename')))
    chk(f'{a}_component_correct_size_answers', g(r, 'component_extensions_sizeof_cfarrayref') == '0' and cnt(r, 'component_extensions_sizeof_cfarrayref') > 0
        and 'wav' in r['component_extensions_sizeof_cfarrayref'].get('values', '').split(','), str(r.get('component_extensions_sizeof_cfarrayref')))
    chk(f'{a}_unknown_extension_no_type', g(r, 'types_for_extension:zzzq') == '0' and cnt(r, 'types_for_extension:zzzq') == 0, str(r.get('types_for_extension:zzzq')))
chk('i386_size4_accepted', g(i, 'component_extensions_size4') == '0' and cnt(i, 'component_extensions_size4') > 0)
chk('x86_64_size4_refused_bad_property_size', g(x, 'component_extensions_size4') == '!siz', str(x.get('component_extensions_size4')))
chk('readable_types_same_both', i.get('readable_types', {}).get('values') and i['readable_types'].get('values') == x.get('readable_types', {}).get('values'),
    f"i386={i.get('readable_types', {}).get('count')} x86_64={x.get('readable_types', {}).get('count')}")
for k in ('extensions_for_WAVE', 'utis_for_WAVE', 'mimes_for_WAVE', 'extensions_for_AIFF', 'all_extensions', 'all_utis', 'all_mimes'):
    chk(f'i386_{k}_filled', g(i, k) == '0' and cnt(i, k) > 0, f"count={cnt(i, k)}")
    chk(f'x86_64_{k}_empty', g(x, k) == '0' and cnt(x, k) == 0, f"count={cnt(x, k)}")
chk('i386_wav_extension_to_WAVE', 'WAVE' in (g(i, 'types_for_extension:wav', 'values') or '').split(','), str(i.get('types_for_extension:wav')))
chk('x86_64_wav_extension_no_type', g(x, 'types_for_extension:wav') == '0' and cnt(x, 'types_for_extension:wav') == 0, str(x.get('types_for_extension:wav')))
# consequences already seen in B13 (reported, not part of the verdict)
for a, r in (('i386', i), ('x86_64', x)):
    for k in ('aiff_nohint', 'aiff_hint_AIFF', 'wav_nohint', 'garbage_wav_nohint', 'garbage_wav_hint_WAVE'):
        print(f"AFM_INFO {a} open:{k} {r.get('open:' + k)}")
ok = all(c[1] for c in checks)
print(f"AFM_SUMMARY checks={len(checks)} failures={sum(not c[1] for c in checks)} verdict={'DEFECT3_REPRODUCED' if ok else 'NOT_REPRODUCED_AS_PREDICTED'}")
sys.exit(0 if ok else 1)
