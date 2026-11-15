#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Exact Depends/Pre-Depends closure of an i386 package from authenticated private indexes.

Usage: resolve_closure.py INDEX_DIR ROOT_PACKAGE OUT.json
Reads the verified indexes (see verify_indexes.py) and the local dpkg database
(read-only, via dpkg-query). Models apt defaults for this host: suites trixie,
trixie-updates, trixie-security at equal priority (highest version wins),
backports excluded (NotAutomatic). Recommends are listed separately.
Never calls apt, never changes dpkg/APT state.
"""
import json
import lzma
import re
import subprocess
import sys
from functools import cmp_to_key
from pathlib import Path

D = Path(sys.argv[1]).resolve()
ROOT = sys.argv[2]
OUT = Path(sys.argv[3])
idx = json.loads((D / 'indexes.json').read_text())


# --- Debian version comparison (Debian Policy 5.6.12) -------------------------
def _order(c):
    if c == '~':
        return -1
    if c.isdigit():
        return 0
    if c.isalpha():
        return ord(c)
    return ord(c) + 256


def _cmp_part(a, b):
    a, b = list(a), list(b)
    while a or b:
        first = 0
        while (a and not a[0].isdigit()) or (b and not b[0].isdigit()):
            ac = _order(a[0]) if a and not a[0].isdigit() else 0
            bc = _order(b[0]) if b and not b[0].isdigit() else 0
            if ac != bc:
                return ac - bc
            if a and not a[0].isdigit():
                a.pop(0)
            if b and not b[0].isdigit():
                b.pop(0)
        na = nb = ''
        while a and a[0].isdigit():
            na += a.pop(0)
        while b and b[0].isdigit():
            nb += b.pop(0)
        first = int(na or 0) - int(nb or 0)
        if first:
            return first
    return 0


def vcmp(x, y):
    def split(v):
        e, _, rest = v.rpartition(':') if ':' in v else ('0', '', v)
        up, _, rev = rest.rpartition('-') if '-' in rest else (rest, '', '0')
        return int(e or 0), up, rev
    ex, ux, rx = split(x)
    ey, uy, ry = split(y)
    return (ex - ey) or _cmp_part(ux, uy) or _cmp_part(rx, ry)


def satisfies(have, op, want):
    c = vcmp(have, want)
    return {'>=': c >= 0, '<=': c <= 0, '>>': c > 0, '<<': c < 0, '=': c == 0}[op]


# --- indexes ------------------------------------------------------------------
def paragraphs(text):
    for para in text.split('\n\n'):
        d, key = {}, None
        for line in para.splitlines():
            if line.startswith(' ') and key:
                d[key] += '\n' + line
            elif ': ' in line or line.endswith(':'):
                key, _, value = line.partition(':')
                d[key] = value.strip()
        if 'Package' in d:
            yield d


cands = {}  # name -> list of records
provides = {}  # virtual -> list of (provider record, version or None)
for suite, entry in idx.items():
    local = D / 'raw' / entry['files']['main/binary-i386/Packages.xz']['local']
    for d in paragraphs(lzma.decompress(local.read_bytes()).decode()):
        d['_suite'] = suite
        cands.setdefault(d['Package'], []).append(d)
for name, lst in cands.items():
    lst.sort(key=cmp_to_key(lambda a, b: vcmp(b['Version'], a['Version'])))
    best = lst[0]
    for p in filter(None, (x.strip() for x in best.get('Provides', '').split(','))):
        m = re.match(r'([^\s(]+)\s*(?:\(=\s*([^)]+)\))?', p)
        provides.setdefault(m.group(1), []).append((best, m.group(2)))

# local dpkg database (read-only)
q = subprocess.run(['dpkg-query', '-W', '-f', '${Package}\t${Architecture}\t${Version}\t${db:Status-Abbrev}\t${Multi-Arch}\n'],
                   capture_output=True, text=True, check=True).stdout
installed = {}
for line in q.splitlines():
    n, a, v, st, ma = line.split('\t')
    if st.startswith('ii'):
        installed.setdefault(n, {})[a] = {'version': v, 'multi_arch': ma}


def parse_rel(field):
    groups = []
    for grp in filter(None, (g.strip() for g in field.split(','))):
        alts = []
        for alt in grp.split('|'):
            m = re.match(r'\s*([^\s(:]+)(?::(\w+))?\s*(?:\((<<|<=|=|>=|>>)\s*([^)]+)\))?', alt)
            alts.append((m.group(1), m.group(2), m.group(3), m.group(4).strip() if m.group(4) else None))
        groups.append(alts)
    return groups


def native_ok(name, archq, op, ver):
    """Dependency already satisfied by an installed package usable across architectures."""
    for arch, info in installed.get(name, {}).items():
        if arch == 'all' or (info['multi_arch'] == 'foreign') or (archq == 'any' and info['multi_arch'] == 'allowed'):
            if not op or satisfies(info['version'], op, ver):
                return f'{name}:{arch} {info["version"]} (installed, {"all" if arch == "all" else "Multi-Arch: " + info["multi_arch"]})'
    return None


def pick(name, archq, op, ver):
    for rec in cands.get(name, []):
        if not op or satisfies(rec['Version'], op, ver):
            return rec, None
    for rec, pv in provides.get(name, []):
        if not op or (pv and satisfies(pv, op, ver)):
            return rec, name
    return None, None


chosen, edges, external, recommends = {}, [], [], {}
todo = [ROOT]
first = cands[ROOT][0]
chosen[ROOT] = first
queue = [first]
while queue:
    rec = queue.pop(0)
    for field in ['Pre-Depends', 'Depends']:
        for alts in parse_rel(rec.get(field, '')):
            done = None
            for name, archq, op, ver in alts:
                cand_rec = cands.get(name, [None])[0]
                if cand_rec and cand_rec.get('Architecture') == 'all':
                    hit = native_ok(name, archq, op, ver)
                    if hit:
                        external.append({'from': rec['Package'], 'dep': name, 'satisfied_by': hit})
                        done = 'ext'
                        break
                hit = native_ok(name, archq, op, ver) if (cand_rec is None or cand_rec.get('Multi-Arch') in ('foreign',) or archq == 'any') else None
                if hit:
                    external.append({'from': rec['Package'], 'dep': name, 'satisfied_by': hit})
                    done = 'ext'
                    break
                r, virt = pick(name, archq, op, ver)
                if r:
                    edges.append({'from': rec['Package'], 'field': field, 'dep': name + (f' ({op} {ver})' if op else ''),
                                  'to': r['Package'], 'via_provides': virt})
                    if r['Package'] not in chosen:
                        chosen[r['Package']] = r
                        queue.append(r)
                    done = r['Package']
                    break
            assert done, (rec['Package'], alts)
    for alts in parse_rel(rec.get('Recommends', '')):
        recommends.setdefault(rec['Package'], []).append(' | '.join(a[0] for a in alts))

rows = []
for name, r in sorted(chosen.items()):
    amd = installed.get(name, {}).get('amd64')
    allv = installed.get(name, {}).get('all')
    skew = None
    if r.get('Multi-Arch') == 'same' and amd:
        c = vcmp(r['Version'], amd['version'])
        skew = 'equal' if c == 0 else ('i386_newer_forces_amd64_upgrade' if c > 0 else 'i386_older_than_amd64_conflict')
    rows.append({'package': name, 'version': r['Version'], 'architecture': r['Architecture'], 'suite': r['_suite'],
                 'multi_arch': r.get('Multi-Arch', ''), 'source': r.get('Source', name),
                 'depends': r.get('Depends', ''), 'pre_depends': r.get('Pre-Depends', ''),
                 'filename': r['Filename'], 'size': int(r['Size']), 'sha256': r['SHA256'],
                 'installed_size_kib': int(r.get('Installed-Size', 0)),
                 'amd64_installed': amd['version'] if amd else None,
                 'all_installed': allv['version'] if allv else None,
                 'version_lock': skew})
res = {'root': ROOT, 'model': 'trixie+trixie-updates+trixie-security, highest version, no backports, Depends+Pre-Depends',
       'indexes': {s: {'date': e['date'], 'inrelease_sha256': e['inrelease_sha256']} for s, e in idx.items()},
       'packages': rows, 'satisfied_outside_i386': external, 'edges': edges, 'recommends': recommends,
       'totals': {'count': len(rows), 'download_bytes': sum(x['size'] for x in rows),
                  'installed_kib': sum(x['installed_size_kib'] for x in rows)}}
OUT.write_text(json.dumps(res, indent=2, ensure_ascii=False) + '\n')
for x in rows:
    print(f"{x['package']:<18} {x['version']:<28} {x['suite']:<16} {x['multi_arch']:<8} amd64={x['amd64_installed']} lock={x['version_lock']}")
for e in external:
    print('EXT', e['from'], '->', e['dep'], ':', e['satisfied_by'])
print('RECOMMENDS', json.dumps(recommends))
print('TOTAL', res['totals'])
