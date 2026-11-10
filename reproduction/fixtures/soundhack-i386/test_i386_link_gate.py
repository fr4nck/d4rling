#!/usr/bin/env python3
"""SH09 static inputs and fail-closed linking tests, no external SoundHack source."""
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

import i386_link_gate as gate

# Original source is not redistributed; a tiny synthetic symbol-compatible
# object exercises the verifier's control paths, not DSP correctness.
SYNTH = r'''
extern double sin(double);
extern float sinf(float);
extern float Pi, twoPi;
float gOmegaPiImag[31], gOmegaPiReal[31];
void InitFFTTable(void) { gOmegaPiImag[0] = (float)sin((double)twoPi);
                          gOmegaPiReal[0] = sinf(Pi); }
void bitreverse(float *x, long n) { if(n > 0) x[0] += Pi; }
void FFT(float *x, long n, short d) {
    if(n > 0) x[0] += (float)sin((double)Pi) + sinf(twoPi) + (float)d;
}
void RealFFT(float *x, long n, short d) {
    if(n > 0) x[0] += sinf(twoPi) + (float)sin((double)Pi) + (float)d;
}
'''


def result_stdout(call):
    output = io.StringIO()
    with contextlib.redirect_stdout(output):
        code = call()
    return code, json.loads(output.getvalue())


class SH09Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not shutil.which('clang'):
            raise unittest.SkipTest('no installed clang')
        cls.temp = tempfile.TemporaryDirectory(prefix='sh09-tests-')
        cls.root = Path(cls.temp.name)
        source = cls.root / 'synthetic.c'
        source.write_text(SYNTH, encoding='ascii')
        cls.target = cls.root / 'synthetic.o'
        subprocess.run(['clang', '-target', 'i386-apple-darwin9', '-nostdinc',
                        '-fno-stack-protector', '-std=c99', '-O1', '-c', str(source),
                        '-o', str(cls.target)], check=True, capture_output=True)
        cls.sha = hashlib.sha256(cls.target.read_bytes()).hexdigest()

    @classmethod
    def tearDownClass(cls):
        if hasattr(cls, 'temp'):
            cls.temp.cleanup()

    def test_check_input_synthetic(self):
        result = gate.inspect_macho(self.target, self.sha)
        self.assertEqual((result['arch'], set(result['defined']), set(result['undefined'])),
                         ('i386', gate.EXPECTED_DEFS, gate.EXPECTED_UNDEFS))

    def test_real_relocations_synthetic(self):
        if not shutil.which('llvm-objdump'):
            self.skipTest('llvm-objdump not installed')
        r = gate.command(['llvm-objdump', '--macho', '--reloc', str(self.target)])
        result = gate.inspect_relocations(r.stdout)
        self.assertGreater(result['count'], 0)
        self.assertTrue(set(result['external_math_calls']) == gate.DYNAMIC_MATH)

    def test_strict_pin_rejects_altered(self):
        with self.assertRaises(gate.Inconclusive):
            gate.inspect_macho(self.target, '0'*64)

    def test_nonexistent_object(self):
        with self.assertRaises(gate.Inconclusive):
            gate.inspect_macho(self.root/'absent.o', None)

    def test_rejects_non_macho(self):
        bad = self.root/'not_macho.o'
        bad.write_bytes(b'ELF'+b'0'*100)
        with self.assertRaises(gate.ContractFailure):
            gate.inspect_macho(bad, None)

    def test_wrong_arch(self):
        src = self.root/'synthetic.c'
        target = self.root/'wrong_arch.o'
        subprocess.run(['clang', '-target', 'x86_64-apple-darwin12', '-nostdinc',
                        '-fno-stack-protector', '-c', str(src), '-o', str(target)],
                       check=True, capture_output=True)
        with self.assertRaises(gate.ContractFailure):
            gate.inspect_macho(target, None)

    def test_missing_tool(self):
        with self.assertRaises(gate.Inconclusive):
            gate.executable('no-such-tool-9ab31dbf')

    def test_globals_match_abi(self):
        with tempfile.TemporaryDirectory() as tmp:
            obj = gate.compile_globals('clang', Path(tmp))
            self.assertTrue(obj.exists())
            from macho_audit import parse
            data = parse(obj.read_bytes(), 'i386')
            self.assertEqual(data['filetype'], 1)
            self.assertEqual(set(data['exports_nlist']), gate.EXPECTED_GLOBAL_DEFS)

    def test_relocation_pair_missing(self):
        s = ('Relocation information (__TEXT,__text) 1 entries\n'
             'address  pcrel length extern type scattered symbolnum/value\n'
             '00000000 False long n/a LOCSDIF True 0x00000300\n')
        with self.assertRaises(gate.ContractFailure):
            gate.inspect_relocations(s)

    def test_relocation_orphan_pair(self):
        s = ('Relocation information (__TEXT,__text) 1 entries\n'
             'address  pcrel length extern type scattered symbolnum/value\n'
             '         False long n/a PAIR True 0x00000300\n')
        with self.assertRaises(gate.ContractFailure):
            gate.inspect_relocations(s)

    def test_relocation_header_count(self):
        s = ('Relocation information (__TEXT,__text) 2 entries\n'
             'address  pcrel length extern type scattered symbolnum/value\n'
             '00000000 True long True VANILLA False _sin\n')
        with self.assertRaises(gate.ContractFailure):
            gate.inspect_relocations(s)

    def test_relocation_unknown_kind_inconclusive(self):
        s = ('Relocation information (__TEXT,__text) 1 entries\n'
             'address  pcrel length extern type scattered symbolnum/value\n'
             '00000000 True long True UNSUPPORTED False _sin\n')
        with self.assertRaises(gate.Inconclusive):
            gate.inspect_relocations(s)

    def test_unexpected_external_relocation(self):
        s = ('Relocation information (__TEXT,__text) 1 entries\n'
             'address  pcrel length extern type scattered symbolnum/value\n'
             '00000000 True long True VANILLA False _hidden\n')
        with self.assertRaises(gate.ContractFailure):
            gate.inspect_relocations(s)

    def test_no_group_is_inconclusive(self):
        with self.assertRaises(gate.Inconclusive):
            gate.inspect_relocations('not an llvm-objdump table')

    def test_pinned_48_count_rejected_on_other(self):
        s = ('Relocation information (__TEXT,__text) 2 entries\n'
             'address  pcrel length extern type scattered symbolnum/value\n'
             '00000000 True long True VANILLA False _sin\n'
             '00000004 True long True VANILLA False _sinf\n')
        with self.assertRaises(gate.ContractFailure):
            gate.inspect_relocations(s, pinned=True)

    def test_input_and_relocation_full_pipeline_no_link(self):
        if not shutil.which('llvm-objdump'):
            self.skipTest('llvm-objdump not installed')
        initial = self.target.read_bytes()
        output = gate.qualify(self.target, expected_sha=self.sha, try_link=False)
        self.assertEqual(output['status'], 'LINK_INPUTS_READY')
        self.assertEqual(initial, self.target.read_bytes())
        self.assertEqual(output['requires_external_math'], ['_sin','_sinf'])

    def test_cli_full_no_link(self):
        if not shutil.which('llvm-objdump'):
            self.skipTest('llvm-objdump not installed')
        code, output = result_stdout(lambda: gate.main(['--object', str(self.target),
            '--expected-sha256', self.sha, '--no-link']))
        self.assertEqual(code, 0)
        self.assertEqual(output['status'], 'LINK_INPUTS_READY')

    def test_linker_fake_success_without_product_rejected(self):
        with tempfile.TemporaryDirectory(prefix='sh09-fake-link-') as tmp:
            folder = Path(tmp)
            fake = folder / 'fake-ld64'
            fake.write_text('#!/bin/sh\nexit 0\n', encoding='ascii')
            fake.chmod(stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR)
            glob = gate.compile_globals('clang', folder)
            with self.assertRaises(gate.ContractFailure):
                gate.attempt_link(str(fake), self.target, glob, folder)

    def test_linker_fake_invalid_macho_rejected(self):
        with tempfile.TemporaryDirectory(prefix='sh09-fake-link-') as tmp:
            folder = Path(tmp)
            fake = folder / 'fake-ld64'
            fake.write_text('#!/bin/sh\nwhile [ "$#" -gt 0 ]; do\n'
                            ' if [ "$1" = "-o" ]; then shift; printf BAD > "$1"; exit 0; fi\n'
                            ' shift\ndone\nexit 1\n', encoding='ascii')
            fake.chmod(stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR)
            glob = gate.compile_globals('clang', folder)
            with self.assertRaises(gate.ContractFailure):
                gate.attempt_link(str(fake), self.target, glob, folder)

    @unittest.skipUnless(os.environ.get('SH08_I386_OBJECT'), 'legitimate SH08 object not supplied')
    def test_original_pinned_fft_object(self):
        p = Path(os.environ['SH08_I386_OBJECT'])
        result = gate.qualify(p, try_link=False)
        self.assertEqual(result['status'], 'LINK_INPUTS_READY')
        self.assertEqual(result['relocations']['count'], 48)
        self.assertEqual(result['relocations']['paired_sectdiff'], 21)
        self.assertEqual(result['relocations']['external_math_calls'], {'_sin':2,'_sinf':2})

    @unittest.skipUnless(os.environ.get('SH08_I386_OBJECT'), 'legitimate SH08 object not supplied')
    @unittest.skipUnless(shutil.which('ld64.lld'), 'ld64.lld not available')
    def test_real_lld_unsupported_arch_must_not_pass(self):
        result = gate.qualify(os.environ['SH08_I386_OBJECT'], try_link=True)
        self.assertEqual(result['status'], 'LINK_TOOLCHAIN_BLOCKED')
        self.assertIn('unsupported -arch i386', result['link_attempt']['linker_message'])


if __name__ == '__main__':
    unittest.main()
