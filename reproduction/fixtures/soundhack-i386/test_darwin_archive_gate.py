#!/usr/bin/env python3
"""SH10 Darwin i386 static archive positive and fail-closed regression suite.

Synthetic fixtures do NOT qualify SoundHack's algorithms. Optional authentic
SH08 object required for source-qualified tests.
GPL-3.0-or-later. No implicit downloads, no Apple SDK, no guest execution.
"""
import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import tempfile
import unittest

import darwin_archive_gate as archive
import i386_link_gate as gate
from test_i386_link_gate import SYNTH


def tool(name):
    return shutil.which(name) is not None


@unittest.skipUnless(tool('clang') and tool('llvm-ar') and tool('llvm-objdump'),
                     'Clang/llvm-ar/llvm-objdump not installed')
class SH10ArchiveTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory(prefix='sh10-tests-')
        cls.addClassCleanup(cls.tmp.cleanup)
        cls.root = Path(cls.tmp.name)
        src = cls.root / 'synth.c'
        src.write_text(SYNTH, encoding='ascii')
        cls.obj = cls.root / 'synth.o'
        subprocess.run(['clang', '-target', 'i386-apple-darwin9', '-nostdinc',
                        '-fno-stack-protector', '-std=c99', '-O1', '-c', str(src),
                        '-o', str(cls.obj)], check=True, capture_output=True, timeout=25)
        cls.pin = hashlib.sha256(cls.obj.read_bytes()).hexdigest()

    def do_main(self, *args):
        with contextlib.redirect_stdout(io.StringIO()) as captured:
            rc = archive.main(['--object', str(self.obj), '--expected-sha256', self.pin, *args])
        return rc, json.loads(captured.getvalue())

    def make_archive(self, folder, *, members=('fft.o', 'globals.o'), format='darwin'):
        folder = Path(folder)
        copies = []
        for member in members:
            f = folder / member
            if member == 'fft.o':
                f.write_bytes(self.obj.read_bytes())
            else:
                globals_src = gate.compile_globals('clang', folder)
                f.write_bytes(globals_src.read_bytes())
            copies.append(f)
        dest = folder / 'test.a'
        subprocess.run(['llvm-ar', f'--format={format}', 'rcD', str(dest),
                        *map(str, copies)], check=True, capture_output=True, timeout=25)
        return dest, copies

    def test_archive_created_and_members_verified(self):
        rc, result = self.do_main()
        self.assertEqual((rc, result['status']), (0, 'DARWIN_ARCHIVE_PASS'))
        a = result['archive']
        self.assertEqual([x['name'] for x in a['members']], ['fft.o','globals.o'])
        self.assertTrue(a['has_symbol_index'])
        self.assertEqual(a['unresolved_after_archive'], ['_sin','_sinf'])
        self.assertEqual(set(a['members'][1]['definitions']), gate.EXPECTED_GLOBAL_DEFS)

    def test_archive_deterministic_after_multiple_invocations(self):
        with tempfile.TemporaryDirectory(prefix='sh10-out-') as tmp:
            one, two = [Path(tmp)/name for name in ('one.a','two.a')]
            for output in (one,two):
                rc, _ = self.do_main('--output',str(output))
                self.assertEqual(rc,0)
            self.assertEqual(one.read_bytes(),two.read_bytes())
            self.assertTrue(one.read_bytes().startswith(b'!<arch>\n'))

    def test_source_object_unchanged(self):
        before = self.obj.read_bytes()
        self.assertEqual(self.do_main()[0],0)
        self.assertEqual(before,self.obj.read_bytes())

    def test_exclusive_output_file_refuses_overwrite(self):
        with tempfile.TemporaryDirectory(prefix='sh10-out-') as tmp:
            output = Path(tmp)/'already.a'
            output.write_bytes(b'PROTECTED')
            rc, result = self.do_main('--output',str(output))
            self.assertEqual((rc,result['status']), (3,'INCONCLUSIVE'))
            self.assertEqual(output.read_bytes(), b'PROTECTED')

    def test_output_symlink_refused(self):
        with tempfile.TemporaryDirectory(prefix='sh10-out-') as tmp:
            target = Path(tmp)/'private'
            target.write_bytes(b'PROTECTED')
            link = Path(tmp)/'link.a'
            link.symlink_to(target)
            rc, result = self.do_main('--output',str(link))
            self.assertEqual((rc,result['status']),(3,'INCONCLUSIVE'))
            self.assertEqual(target.read_bytes(), b'PROTECTED')

    def test_missing_clang_is_inconclusive(self):
        rc, result = self.do_main('--clang', 'unavailable-clang-98371')
        self.assertEqual((rc,result['status']),(3,'INCONCLUSIVE'))

    def test_missing_archiver_is_inconclusive(self):
        rc, result = self.do_main('--llvm-ar','unavailable-ar-33237')
        self.assertEqual((rc,result['status']),(3,'INCONCLUSIVE'))

    def test_wrong_sha_rejected_without_output(self):
        output = self.root/'must-not-create.a'
        rc, result = self.do_main('--expected-sha256','0'*64, '--output',str(output))
        self.assertEqual((rc,result['status']),(3,'INCONCLUSIVE'))
        self.assertFalse(output.exists())

    def test_wrong_architecture_rejected(self):
        with tempfile.TemporaryDirectory(prefix='sh10-bad-') as tmp:
            target=Path(tmp)/'wrong.o'
            subprocess.run(['clang','-target','x86_64-apple-darwin12','-nostdinc',
                            '-c',str(self.root/'synth.c'),'-o',str(target)],
                           check=True,capture_output=True,timeout=25)
            with self.assertRaises(gate.ContractFailure):
                archive.qualify(target, hashlib.sha256(target.read_bytes()).hexdigest())

    def test_archive_without_companion_rejected(self):
        with tempfile.TemporaryDirectory(prefix='sh10-bad-') as tmp:
            path, files=self.make_archive(tmp, members=('fft.o',))
            with self.assertRaises(gate.ContractFailure):
                archive.check_archive(path,'llvm-ar',self.obj.read_bytes(),b'')

    def test_archive_wrong_order_rejected(self):
        with tempfile.TemporaryDirectory(prefix='sh10-bad-') as tmp:
            path, files=self.make_archive(tmp, members=('globals.o','fft.o'))
            with self.assertRaises(gate.ContractFailure):
                archive.check_archive(path,'llvm-ar',self.obj.read_bytes(),b'')

    def test_non_darwin_ar_index_rejected(self):
        with tempfile.TemporaryDirectory(prefix='sh10-bad-') as tmp:
            path, files=self.make_archive(tmp, format='gnu')
            with self.assertRaises(gate.ContractFailure):
                archive.check_archive(path,'llvm-ar',self.obj.read_bytes(),(Path(tmp)/'globals.o').read_bytes())

    def test_mutated_member_detected_by_byte_comparison(self):
        with tempfile.TemporaryDirectory(prefix='sh10-tamper-') as tmp:
            path, files = self.make_archive(tmp)
            altered = bytearray(self.obj.read_bytes())
            altered[720] ^= 1
            (Path(tmp)/'fft.o').write_bytes(altered)
            subprocess.run(['llvm-ar','--format=darwin','rD',str(path),str(Path(tmp)/'fft.o')],
                           check=True, capture_output=True, timeout=25)
            with self.assertRaises(gate.ContractFailure):
                archive.check_archive(path,'llvm-ar',self.obj.read_bytes(),
                                      (Path(tmp)/'globals.o').read_bytes())

    def test_cctools_linker_command_has_expected_flags(self):
        with tempfile.TemporaryDirectory(prefix='sh10-cctools-') as tmp:
            path, members = self.make_archive(tmp)
            argv = Path(tmp)/'args'
            fake=Path(tmp)/'ld64'
            fake.write_text('#!/bin/sh\nprintf "%s\\n" "$@" > "'+str(argv)+'"\n'
                            'echo intentional-test-failure >&2\nexit 1\n',encoding='ascii')
            fake.chmod(0o700)
            result = archive.try_link_archive(path,str(fake),Path(tmp))
            self.assertEqual(result['status'],'LINK_TOOLCHAIN_BLOCKED')
            received = argv.read_text().splitlines()
            self.assertIn('-arch',received)
            self.assertIn('i386',received)
            self.assertIn('-all_load',received)
            self.assertIn('-macosx_version_min',received)
            self.assertIn('10.5',received)
            self.assertIn(str(path),received)
            self.assertIn('-install_name',received)
            self.assertIn(gate.INSTALL_NAME,received)
            self.assertIn('-undefined',received)
            self.assertIn('dynamic_lookup',received)

    def test_padding_error_rejected(self):
        with tempfile.TemporaryDirectory(prefix='sh10-bad-') as tmp:
            path, files=self.make_archive(tmp)
            raw=self.obj.read_bytes()
            self.assertNotEqual(raw,raw+b'X')
            with self.assertRaises(gate.ContractFailure):
                archive.check_archive(path,'llvm-ar',raw+b'X', (Path(tmp)/'globals.o').read_bytes())

    def test_fake_archive_tool_no_output_rejected(self):
        with tempfile.TemporaryDirectory(prefix='sh10-fake-') as tmp:
            fake=Path(tmp)/'fake-ar'
            fake.write_text('#!/bin/sh\nexit 0\n',encoding='ascii')
            fake.chmod(stat.S_IRUSR|stat.S_IWUSR|stat.S_IXUSR)
            rc, result=self.do_main('--llvm-ar',str(fake))
            self.assertEqual((rc,result['status']),(2,'TARGET_CONTRACT_FAIL'))

    def test_fake_linker_success_without_output_rejected(self):
        with tempfile.TemporaryDirectory(prefix='sh10-fake-') as tmp:
            fake=Path(tmp)/'fake-ld64'
            fake.write_text('#!/bin/sh\nexit 0\n',encoding='ascii')
            fake.chmod(0o700)
            rc, result=self.do_main('--ld64',str(fake))
            self.assertEqual((rc,result['status']),(2,'TARGET_CONTRACT_FAIL'))

    def test_fake_linker_invalid_output_rejected(self):
        with tempfile.TemporaryDirectory(prefix='sh10-fake-') as tmp:
            fake=Path(tmp)/'fake-ld64'
            fake.write_text('#!/bin/sh\nwhile [ "$#" -gt 0 ]; do\n'
                            ' if [ "$1" = "-o" ]; then shift; printf BAD > "$1"; exit 0; fi\n'
                            ' shift\ndone\nexit 1\n', encoding='ascii')
            fake.chmod(0o700)
            rc, result=self.do_main('--ld64',str(fake))
            self.assertEqual((rc,result['status']),(2,'TARGET_CONTRACT_FAIL'))

    @unittest.skipUnless(tool('ld64.lld'), 'LLVM ld64.lld not installed')
    def test_current_lld_rejects_i386_and_cannot_pass(self):
        rc, result=self.do_main('--ld64','ld64.lld')
        self.assertEqual((rc,result['status']),(3,'LINK_TOOLCHAIN_BLOCKED'))
        self.assertIn('unsupported -arch i386',result['link_attempt']['linker_stderr_tail'])

    @unittest.skipUnless(bool(os.environ.get('SH08_I386_OBJECT')),
                         'legitimate original SH08 object unavailable; pass SH08_I386_OBJECT')
    def test_real_original_sh08_archive(self):
        source=Path(os.environ['SH08_I386_OBJECT'])
        result=archive.qualify(source)
        self.assertEqual(result['status'],'DARWIN_ARCHIVE_PASS')
        self.assertEqual(result['archive']['members'][0]['original_sha256'],gate.EXPECTED_SH08_SHA256)
        self.assertEqual(result['archive']['unresolved_after_archive'],['_sin','_sinf'])
        self.assertEqual(result['archive']['members'][0]['darwin_padding_lf_bytes'],4)


if __name__ == '__main__':
    unittest.main()
