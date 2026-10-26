"""JACK-01E1: offline PCM contract model (not a JACK, RT or ABI test).

This preserves the 12 model tests first executed by the user on the 5700X
on 2026-10-26: 12/12 PASS, 0 failures, Python stdlib only.

This Python implementation allocates memory inside cycle(), is not thread-safe
and must NOT be used as an audio callback or as a production backend.
"""
import sys
import unittest


class PCM:
    def __init__(self, channels=2, capacity=2048, rate=48000):
        if channels not in (1, 2) or capacity < 1 or rate <= 0:
            raise ValueError("invalid configuration")
        self.channels = channels
        self.capacity = capacity
        self.rate = rate
        self.buffers = [[0.0] * capacity for _ in range(channels)]
        self.rd = self.wr = self.queued = 0
        self.clock = self.overruns = self.underrun_frames = 0
        self.running = False

    def start(self):
        if self.running:
            return False
        self.running = True
        return True

    def stop(self):
        if not self.running:
            return False
        self.running = False
        self.queued = 0
        self.rd = self.wr
        return True

    def write(self, planar):
        if not self.running:
            return False
        if len(planar) != self.channels:
            raise ValueError("channel mismatch")
        lengths = {len(channel) for channel in planar}
        if len(lengths) != 1:
            raise ValueError("frame mismatch")
        n = lengths.pop()
        if n > self.capacity - self.queued:
            self.overruns += 1
            return False
        for i in range(n):
            pos = (self.wr + i) % self.capacity
            for c in range(self.channels):
                self.buffers[c][pos] = planar[c][i]
        self.wr = (self.wr + n) % self.capacity
        self.queued += n
        return True

    def cycle(self, n):
        if n < 0:
            raise ValueError("negative frame count")
        if not self.running:
            return [[0.0] * n for _ in range(self.channels)]
        take = min(n, self.queued)
        result = []
        for c in range(self.channels):
            result.append([
                self.buffers[c][(self.rd + i) % self.capacity]
                for i in range(take)
            ] + [0.0] * (n - take))
        self.rd = (self.rd + take) % self.capacity
        self.queued -= take
        self.clock += n
        self.underrun_frames += n - take
        return result


class Contract(unittest.TestCase):
    def test_frame_sizes(self):
        for n in (0, 1, 64, 128, 1024):
            with self.subTest(n=n):
                p = PCM(capacity=2048)
                p.start()
                samples = [[1.0] * n, [2.0] * n]
                self.assertTrue(p.write(samples))
                self.assertEqual(p.cycle(n), samples)

    def test_sample_rates(self):
        for rate in (44100, 48000, 96000):
            with self.subTest(rate=rate):
                p = PCM(rate=rate)
                p.start()
                p.cycle(128)
                self.assertAlmostEqual(
                    p.clock / p.rate, 128 / rate
                )

    def test_planar_channel_independence(self):
        p = PCM()
        p.start()
        p.write([[1.0, 2.0], [10.0, 20.0]])
        self.assertEqual(
            p.cycle(2), [[1.0, 2.0], [10.0, 20.0]]
        )

    def test_mono(self):
        p = PCM(channels=1)
        p.start()
        p.write([[0.5, -0.5]])
        self.assertEqual(p.cycle(2), [[0.5, -0.5]])

    def test_wraparound(self):
        p = PCM(capacity=4)
        p.start()
        p.write([[1, 2, 3], [11, 12, 13]])
        self.assertEqual(p.cycle(2), [[1, 2], [11, 12]])
        self.assertTrue(p.write([[4, 5], [14, 15]]))
        self.assertEqual(
            p.cycle(3), [[3, 4, 5], [13, 14, 15]]
        )

    def test_underrun_zero_fill(self):
        p = PCM()
        p.start()
        p.write([[1.0], [2.0]])
        self.assertEqual(
            p.cycle(4),
            [[1.0, 0.0, 0.0, 0.0],
             [2.0, 0.0, 0.0, 0.0]]
        )
        self.assertEqual(p.underrun_frames, 3)

    def test_overflow_atomicity(self):
        p = PCM(capacity=3)
        p.start()
        p.write([[1, 2], [11, 12]])
        self.assertFalse(p.write([[3, 4], [13, 14]]))
        self.assertEqual(p.overruns, 1)
        self.assertEqual(p.queued, 2)
        self.assertEqual(p.cycle(2), [[1, 2], [11, 12]])

    def test_stop_restart(self):
        p = PCM()
        self.assertTrue(p.start())
        p.write([[1], [2]])
        self.assertTrue(p.stop())
        self.assertFalse(p.running)
        self.assertTrue(p.start())
        self.assertEqual(p.cycle(1), [[0.0], [0.0]])

    def test_clock_monotonic(self):
        p = PCM()
        p.start()
        p.cycle(64)
        p.cycle(128)
        self.assertEqual(p.clock, 192)

    def test_invalid_shape(self):
        p = PCM()
        p.start()
        with self.assertRaises(ValueError):
            p.write([[1, 2]])
        with self.assertRaises(ValueError):
            p.write([[1], [2, 3]])

    def test_negative_cycle_rejected(self):
        p = PCM()
        p.start()
        with self.assertRaises(ValueError):
            p.cycle(-1)

    def test_no_write_while_stopped(self):
        p = PCM()
        self.assertFalse(p.write([[1], [2]]))
        self.assertEqual(p.queued, 0)


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(Contract)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    passed = result.testsRun - len(result.failures) - len(result.errors)
    print(f"JACK01E1_PASS={passed}/{result.testsRun}")
    print(f"JACK01E1_FAIL={len(result.failures) + len(result.errors)}")
    print(
        "JACK01E1_STATUS="
        + ("PASS_MODEL_ONLY" if result.wasSuccessful() else "FAIL")
    )
    print("REAL_JACK_TEST=NOT_EXECUTED")
    print("FILES_MODIFIED=NO")
    sys.exit(0 if result.wasSuccessful() else 1)
