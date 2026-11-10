#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""M2 bounded synthetic-contract tests; does not manufacture a real dylib."""
from __future__ import annotations

from copy import deepcopy
import importlib.util
from pathlib import Path
import subprocess
import struct
import sys
import unittest

SOURCE = Path(__file__).with_name('check_c4d_macho_i386.py')
spec = importlib.util.spec_from_file_location('c4d_m2_gate', SOURCE)
assert spec is not None and spec.loader is not None
m2 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m2)


def fixture():
    qt_id = '/System/Library/Frameworks/QuickTime.framework/Versions/A/QuickTime'
    cs_id = '/System/Library/Frameworks/CoreServices.framework/Versions/A/CoreServices'
    cc_id = ('/System/Library/Frameworks/CoreServices.framework/Frameworks/'
             'CarbonCore.framework/Versions/A/CarbonCore')

    def node(name, ident, imports=(), exports=(), deps=()):
        return {
            'arch': 'i386', 'cputype': 7, 'bits': 32, 'filetype': 6,
            'install_name': ident, 'dylibs': list(deps), 'has_symtab': True,
            'has_dyld_info': False, 'two_level_namespace': True,
            'exports_nlist': list(exports),
            'imports_detail': [
                {'name': s, 'lookup': 'library', 'library_name': cs_id,
                 'weak_import': False, 'common_or_prebound': False,
                 'reference_to_weak': False} for s in imports
            ],
        }
    return {
        'QuickTime': node('QuickTime', qt_id, m2.SYMS, ['_GetMediaSample'],
                          [{'kind': 'load', 'name': cs_id}]),
        'CoreServices': node('CoreServices', cs_id, (), (),
                             [{'kind': 'reexport', 'name': cc_id}]),
        'CarbonCore': node('CarbonCore', cc_id, (), m2.SYMS),
    }


class TestC4DM2(unittest.TestCase):
    def evaluate(self, images=None):
        return m2.assess(fixture() if images is None else images)

    def test_positive_scope_is_static_only(self):
        result = self.evaluate()
        self.assertEqual((result['status'], result['exit_code']), ('STATIC_GATE_PASS', 0))
        self.assertTrue(any('no C4 ABI' in x for x in result['limitations']))

    def test_does_not_modify_input(self):
        images = fixture()
        original = deepcopy(images)
        self.evaluate(images)
        self.assertEqual(images, original)

    def test_missing_core_reexport_fails(self):
        images = fixture()
        images['CoreServices']['dylibs'] = []
        self.assertEqual(self.evaluate(images)['exit_code'], 2)

    def test_load_is_not_reexport(self):
        images = fixture()
        images['CoreServices']['dylibs'][0]['kind'] = 'load'
        self.assertIn('LC_REEXPORT_DYLIB', ' '.join(self.evaluate(images)['errors']))

    def test_missing_quicktime_load_fails(self):
        images = fixture()
        images['QuickTime']['dylibs'] = []
        self.assertEqual(self.evaluate(images)['exit_code'], 2)

    def test_duplicate_core_load_fails(self):
        images = fixture()
        images['QuickTime']['dylibs'] *= 2
        self.assertEqual(self.evaluate(images)['exit_code'], 2)

    def test_direct_carbon_dependency_fails(self):
        images = fixture()
        images['QuickTime']['dylibs'].append(images['CoreServices']['dylibs'][0].copy())
        self.assertIn('direct CarbonCore', ' '.join(self.evaluate(images)['errors']))

    def test_core_reexport_id_mismatch_inconclusive(self):
        images = fixture()
        images['CoreServices']['dylibs'][0]['name'] = '@rpath/CarbonCore.framework/Versions/A/CarbonCore'
        self.assertEqual(self.evaluate(images)['exit_code'], 3)

    def test_quicktime_id_mismatch_inconclusive(self):
        images = fixture()
        images['QuickTime']['dylibs'][0]['name'] = '@rpath/CoreServices.framework/Versions/A/CoreServices'
        self.assertEqual(self.evaluate(images)['exit_code'], 3)

    def test_wrong_ordinal_supplier_fails(self):
        images = fixture()
        images['QuickTime']['imports_detail'][0]['library_name'] = images['CarbonCore']['install_name']
        self.assertIn('wrong dylib ordinal', ' '.join(self.evaluate(images)['errors']))

    def test_weak_memory_import_fails(self):
        images = fixture()
        images['QuickTime']['imports_detail'][0]['weak_import'] = True
        self.assertIn('weak-imported', ' '.join(self.evaluate(images)['errors']))

    def test_dynamic_lookup_inconclusive(self):
        images = fixture()
        images['QuickTime']['imports_detail'][0]['lookup'] = 'dynamic_lookup'
        self.assertEqual(self.evaluate(images)['exit_code'], 3)

    def test_no_import_detail_inconclusive(self):
        images = fixture()
        images['QuickTime']['imports_detail'] = []
        self.assertEqual(self.evaluate(images)['exit_code'], 3)

    def test_duplicate_import_ambiguous(self):
        images = fixture()
        images['QuickTime']['imports_detail'].append(images['QuickTime']['imports_detail'][0].copy())
        self.assertEqual(self.evaluate(images)['exit_code'], 3)

    def test_flat_namespace_inconclusive(self):
        images = fixture()
        images['QuickTime']['two_level_namespace'] = False
        self.assertEqual(self.evaluate(images)['exit_code'], 3)

    def test_dyld_info_present_on_quicktime_is_inconclusive(self):
        images = fixture()
        images['QuickTime']['has_dyld_info'] = True
        result = self.evaluate(images)
        self.assertEqual((result['status'], result['exit_code']), ('STATIC_INCONCLUSIVE', 3))
        self.assertIn('LC_DYLD_INFO', ' '.join(result['inconclusive']))

    def test_dyld_info_present_on_coreservices_is_inconclusive(self):
        images = fixture()
        images['CoreServices']['has_dyld_info'] = True
        self.assertEqual(self.evaluate(images)['exit_code'], 3)

    def test_dyld_info_present_on_carboncore_is_inconclusive(self):
        images = fixture()
        images['CarbonCore']['has_dyld_info'] = True
        self.assertEqual(self.evaluate(images)['exit_code'], 3)

    def test_dyld_info_does_not_hide_missing_reexport_failure(self):
        images = fixture()
        images['CoreServices']['has_dyld_info'] = True
        images['CoreServices']['dylibs'].clear()
        result = self.evaluate(images)
        self.assertEqual((result['status'], result['exit_code']), ('STATIC_FAIL', 2))
        self.assertIn('LC_REEXPORT_DYLIB', ' '.join(result['errors']))

    def test_missing_symtab_inconclusive(self):
        images = fixture()
        images['QuickTime']['has_symtab'] = False
        self.assertEqual(self.evaluate(images)['exit_code'], 3)

    def test_missing_memerror_inconclusive_not_false_pass(self):
        images = fixture()
        images['CarbonCore']['exports_nlist'].remove('_MemError')
        self.assertEqual(self.evaluate(images)['exit_code'], 3)

    def test_missing_getmediasample_inconclusive(self):
        images = fixture()
        images['QuickTime']['exports_nlist'] = []
        self.assertEqual(self.evaluate(images)['exit_code'], 3)

    def test_wrong_cpu_fails(self):
        images = fixture()
        images['QuickTime']['cputype'] = 0x01000007
        self.assertEqual(self.evaluate(images)['exit_code'], 2)

    def test_wrong_mach_type_fails(self):
        images = fixture()
        images['CarbonCore']['filetype'] = 2
        self.assertEqual(self.evaluate(images)['exit_code'], 2)

    def test_fake_install_name_fails(self):
        images = fixture()
        images['CoreServices']['install_name'] = '/tmp/CoreServices'
        self.assertEqual(self.evaluate(images)['exit_code'], 2)

    def test_framework_paths_are_not_basename_matches(self):
        self.assertTrue(m2.framework_path('@rpath/X.framework/Versions/A/X', 'X'))
        self.assertTrue(m2.framework_path('@loader_path/X.framework/X', 'X'))
        self.assertFalse(m2.framework_path('/tmp/X', 'X'))
        self.assertFalse(m2.framework_path('/tmp/X.framework/fake/X', 'X'))

    def test_duplicate_input_files_blocked_before_reader(self):
        cmd = [sys.executable, str(SOURCE), '--quicktime', '/tmp/X',
               '--coreservices', '/tmp/X', '--carboncore', '/tmp/Y']
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        self.assertEqual(result.returncode, 3)
        self.assertIn('distinct dylib files', result.stdout)

    def test_real_shared_reader_synthetic_chain_when_checkout_available(self):
        if not m2.PARSER.is_file():
            self.skipTest('full D4rling checkout/shared Mach-O reader not mounted')
        reader = m2.load_reader()
        sys.path.insert(0, str(m2.PARSER.parent))
        try:
            from test_macho_audit import thin
        finally:
            sys.path.pop(0)
        ids = {name: fixture()[name]['install_name'] for name in m2.FRAMEWORKS}
        qt = thin(install_name=ids['QuickTime'], dylibs=[ids['CoreServices']],
                  imports=[(symbol, 1, False) for symbol in m2.SYMS],
                  exports=['_GetMediaSample'], two_level=True)
        core = bytearray(thin(install_name=ids['CoreServices'],
                              dylibs=[ids['CarbonCore']], two_level=True))
        # Transform only the second dylib load command (after LC_ID_DYLIB)
        # into LC_REEXPORT_DYLIB; reuses the existing fixture generator.
        ncmds = struct.unpack_from('<I', core, 16)[0]
        pos = 28
        changed = 0
        for _ in range(ncmds):
            cmd, size = struct.unpack_from('<II', core, pos)
            if cmd == 0xC:
                struct.pack_into('<I', core, pos, 0x8000001F)
                changed += 1
            pos += size
        self.assertEqual(changed, 1)
        carbon = thin(install_name=ids['CarbonCore'], exports=m2.SYMS, two_level=True)
        images = {'QuickTime': reader.parse(qt, 'i386'),
                  'CoreServices': reader.parse(bytes(core), 'i386'),
                  'CarbonCore': reader.parse(carbon, 'i386')}
        self.assertEqual(m2.assess(images)['status'], 'STATIC_GATE_PASS')
        # A distinct parse without reexport must fail the M2 structural gate.
        no_reexport = reader.parse(thin(install_name=ids['CoreServices'],
                                       dylibs=[ids['CarbonCore']], two_level=True), 'i386')
        images['CoreServices'] = no_reexport
        self.assertEqual(m2.assess(images)['exit_code'], 2)

    def test_real_reader_rejects_wrong_arch_when_checkout_available(self):
        if not m2.PARSER.is_file():
            self.skipTest('full D4rling checkout/shared Mach-O reader not mounted')
        reader = m2.load_reader()
        sys.path.insert(0, str(m2.PARSER.parent))
        try:
            from test_macho_audit import thin
        finally:
            sys.path.pop(0)
        with self.assertRaises(reader.InvalidMachO):
            reader.parse(thin('x86_64'), 'i386')


if __name__ == '__main__':
    unittest.main()
