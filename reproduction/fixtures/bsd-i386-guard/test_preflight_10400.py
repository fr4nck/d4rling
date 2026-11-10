import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch

import preflight_10400 as p

class Check10400(unittest.TestCase):
    def test_no_dirs(self):
        with tempfile.TemporaryDirectory() as d:
            t=Path(d)
            result=p.inventory(t)
            self.assertEqual(result['CANON'],'MISSING')
            self.assertEqual(result['HIST'],'MISSING')
            self.assertEqual(result['PINNED_XNU_OBJECTS'],'NOT_FOUND_IN_KNOWN_PATHS')
            self.assertEqual(list(t.iterdir()),[])

    def test_existing_layout_no_mutation(self):
        with tempfile.TemporaryDirectory() as d:
            t=Path(d)
            roots=(t/'atelier'/'d4rling', t/'atelier'/'d4rling-10400'/'source',
                   t/'atelier'/'d4rling-10400'/'build-core-i386',t/'atelier'/'d4rling-r4f-20261110-182414')
            for root in roots:root.mkdir(parents=True)
            before=set(map(str,t.rglob('*')))
            result=p.inventory(t)
            after=set(map(str,t.rglob('*')))
            self.assertEqual(before,after)
            self.assertTrue(all(result[k]=='PRESENT' for k in ('CANON','HIST','BUILD','OUT_EXISTING')))

    def test_xnu_candidates_not_created(self):
        with tempfile.TemporaryDirectory() as d:
            t=Path(d)
            q=t/'src'/'external'/'darling-xnu'
            q.mkdir(parents=True)
            self.assertIn(q,p.xnu_candidates(t,t))

    def test_non_git_fails_closed(self):
        with tempfile.TemporaryDirectory() as d:
            ok,info=p.probe_git(Path(d),'rev-parse','--verify','HEAD')
            self.assertFalse(ok)

    def test_do_not_touch_outside_existing_dirs(self):
        with tempfile.TemporaryDirectory() as d:
            t=Path(d)
            p.inventory(t)
            self.assertFalse((t/'atelier').exists())

    def test_no_absent_private_install_asserted_present(self):
        with tempfile.TemporaryDirectory() as d:
            result=p.inventory(Path(d))
            self.assertEqual(result['PRIVATE_MLDR32'],'MISSING_OR_OTHER_LAYOUT')
            self.assertEqual(result['PRIVATE_LIBSYSTEM_FAT'],'MISSING_OR_OTHER_LAYOUT')

    def test_wsl_message_has_no_guessed_qualification(self):
        with tempfile.TemporaryDirectory() as d:
            result=p.inventory(Path(d))
            self.assertIn(result['WSL2'],('PRESENT','NOT_DETECTED'))
            self.assertEqual(result['SAFE_SCOPE'],'READ_ONLY_NO_NETWORK_NO_INSTALL_NO_DELETE')

if __name__=='__main__':unittest.main()
