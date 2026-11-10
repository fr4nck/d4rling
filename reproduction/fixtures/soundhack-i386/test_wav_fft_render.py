#!/usr/bin/env python3
"""SH07 WAV reader/renderer host qualification and adversarial cases."""
# Copyright (C) 2026 D4rling contributors; GPL-3.0-or-later.
import contextlib
import io
import json
import math
import os
from pathlib import Path
import shutil
import struct
import tempfile
import unittest
import wave

import wav_fft_render as render

MATH_DIR = Path(os.environ.get('SOUNDHACK_MATH_DIR', '/missing-external-soundhack-source'))


class SoundHackWavTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='sh07-test-')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.ins = self.root/'input.wav'
        self.out = self.root/'filtered.wav'

    def wave(self, samples, rate=48000, channels=1, width=2):
        if width == 2:
            payload = struct.pack('<' + 'h'*len(samples), *[round(max(-1.0, min(0.999969, x))*32768) for x in samples])
        elif width == 1:
            payload = bytes([max(0, min(255, round(x*128 + 128))) for x in samples])
        else:
            raise ValueError(width)
        with wave.open(str(self.ins), 'wb') as wav:
            wav.setnchannels(channels)
            wav.setsampwidth(width)
            wav.setframerate(rate)
            wav.writeframes(payload)

    def sinmix(self, n=4800, rate=48000):
        return [0.45*math.sin(2*math.pi*750*i/rate) +
                0.25*math.sin(2*math.pi*3000*i/rate) for i in range(n)]

    def render(self, freq=3000, fft=1024, radius=2):
        return render.render(MATH_DIR, self.ins, self.out, freq, fft, radius)

    @staticmethod
    def component(samples, rate, hz):
        n = len(samples)
        co = sum(v*math.cos(2*math.pi*hz*i/rate) for i,v in enumerate(samples))
        si = sum(v*math.sin(2*math.pi*hz*i/rate) for i,v in enumerate(samples))
        return 2*math.hypot(co,si)/n

    def test_missing_input_refused(self):
        with self.assertRaisesRegex(render.Inconclusive, 'absent'):
            render.read_wav(self.ins)
        self.assertFalse(self.out.exists())

    def test_truncated_riff_refused(self):
        self.ins.write_bytes(b'RIFF' + b'\x00'*20)
        with self.assertRaises(render.Inconclusive):
            render.read_wav(self.ins)

    def test_non_wav_refused(self):
        self.ins.write_bytes(b'not a wav')
        with self.assertRaises(render.Inconclusive):
            render.read_wav(self.ins)

    def test_pcm8_refused(self):
        self.wave([0.0]*128, width=1)
        with self.assertRaisesRegex(render.Inconclusive, 'mono, uncompressed, 16-bit'):
            render.read_wav(self.ins)

    def test_stereo_refused(self):
        self.wave([0.0]*256, channels=2)
        with self.assertRaisesRegex(render.Inconclusive, 'mono, uncompressed, 16-bit'):
            render.read_wav(self.ins)

    def test_sample_limit_refused(self):
        self.wave([0.0]*2500, rate=7999)
        with self.assertRaisesRegex(render.Inconclusive, 'out of bounds'):
            render.read_wav(self.ins)

    def test_oversized_input_refused(self):
        self.ins.write_bytes(b'A' * (render.MAX_INPUT_BYTES + 1))
        with self.assertRaisesRegex(render.Inconclusive, 'exceeds'):
            render.read_wav(self.ins)

    def test_frequency_refused(self):
        samples = [0.0]*64
        for hz in (float('nan'),float('inf'),-2,0,24000,30000):
            with self.subTest(hz=hz), self.assertRaises(render.Inconclusive):
                render.validate(48000,samples,hz,1024,1)

    def test_invalid_bin_and_radius_refused(self):
        samples = [0.0]*128
        for (hz,fft,radius) in [(3,1024,2),(23990,1024,2),(3000,1024,-1),(3000,1024,7),(3000,333,2)]:
            with self.subTest(hz=hz,fft=fft,radius=radius), self.assertRaises(render.Inconclusive):
                render.validate(48000,samples,hz,fft,radius)

    def test_output_collision_refused_without_overwrite(self):
        self.wave(self.sinmix(n=512))
        self.out.write_bytes(b'protected-existing-user-file')
        with self.assertRaisesRegex(render.Inconclusive, 'destination already exists'):
            self.render()
        self.assertEqual(self.out.read_bytes(),b'protected-existing-user-file')

    def test_symlink_destination_refused(self):
        self.wave(self.sinmix(n=512))
        marker=self.root/'protected.bin'; marker.write_bytes(b'protected')
        self.out.symlink_to(marker)
        with self.assertRaisesRegex(render.Inconclusive, 'destination already exists'):
            self.render()
        self.assertEqual(marker.read_bytes(),b'protected')

    def test_read_pcm16_values(self):
        self.wave([0.0, 0.5, -0.5, 0.99])
        rate, samples=render.read_wav(self.ins)
        self.assertEqual(rate,48000)
        self.assertEqual(len(samples),4)
        self.assertLess(max(abs(a-b) for a,b in zip(samples,[0,0.5,-0.5,0.99])),1/32768)

    def test_refuses_missing_pinned_math_before_writing(self):
        self.wave(self.sinmix(n=512))
        with self.assertRaisesRegex(render.Inconclusive, "missing source"):
            render.render(self.root / "missing-math", self.ins, self.out, 3000)
        self.assertFalse(self.out.exists())

    def test_cli_invalid_returns_3_no_file(self):
        self.wave(self.sinmix(n=256))
        with contextlib.redirect_stdout(io.StringIO()) as out:
            ret=render.main(['--math-dir','/definitely/missing','--input',str(self.ins),
                             '--output',str(self.out),'--notch-hz','3000'])
        self.assertEqual(ret,3)
        self.assertEqual(json.loads(out.getvalue())['status'],'INCONCLUSIVE')
        self.assertFalse(self.out.exists())

    @unittest.skipUnless(MATH_DIR.exists() and shutil.which('cc'), 'pinned upstream source and C compiler required')
    def test_real_wave_processing_and_spectral_reduction(self):
        self.wave(self.sinmix(n=48000))
        info=self.render()
        self.assertEqual(info['status'],'HOST_WAV_RENDERED')
        self.assertEqual(info['frames'],48000)
        r1,a=render.read_wav(self.ins)
        r2,b=render.read_wav(self.out)
        self.assertEqual((r1,len(a)),(r2,len(b)))
        before_3000=self.component(a,r1,3000)
        after_3000=self.component(b,r2,3000)
        self.assertLess(after_3000/before_3000,0.01)
        self.assertLess(abs(self.component(b,r2,750)-self.component(a,r1,750)),0.005)
        self.assertLess(max(abs(v) for v in b),1)

    @unittest.skipUnless(MATH_DIR.exists() and shutil.which('cc'), 'pinned upstream source and C compiler required')
    def test_real_short_nonmultiple_input(self):
        self.wave(self.sinmix(n=2099))
        self.render(fft=512,radius=1)
        rate,b=render.read_wav(self.out)
        self.assertEqual(rate,48000)
        self.assertEqual(len(b),2099)
        self.assertTrue(all(math.isfinite(v) for v in b))

    @unittest.skipUnless(MATH_DIR.exists() and shutil.which('cc'), 'pinned upstream source and C compiler required')
    def test_real_silence_stays_silent(self):
        self.wave([0.0]*3020)
        self.render()
        _,b=render.read_wav(self.out)
        self.assertEqual(max(abs(v) for v in b),0.0)

    @unittest.skipUnless(MATH_DIR.exists() and shutil.which('cc'), 'pinned upstream source and C compiler required')
    def test_real_pinned_source_mutation_rejected(self):
        self.wave(self.sinmix(n=512))
        rogue=self.root/'invalidmath';rogue.mkdir()
        (rogue/'FFT.c').write_bytes(b'void malformed() {}')
        (rogue/'FFT.h').write_bytes((MATH_DIR/'FFT.h').read_bytes())
        with self.assertRaisesRegex(render.Inconclusive, 'unexpected Git blob'):
            render.render(rogue, self.ins,self.out,3000)
        self.assertFalse(self.out.exists())


if __name__=='__main__':
    unittest.main()
