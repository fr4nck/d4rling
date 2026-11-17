#!/usr/bin/env python3
"""SH21 synthetic unit tests; no vendor binary or external executable used."""

import contextlib
import hashlib
import io
import json
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

import sh21_import_closure as gate


class SH21SyntheticTests(unittest.TestCase):
    def setUp(self):
        t = tempfile.TemporaryDirectory()
        self.addCleanup(t.cleanup)
        self.root = Path(t.name)
        self.app = self.root / "SoundHack.app"
        self.bin = self.app / "Contents" / "MacOS" / "SoundHack"
        self.bin.parent.mkdir(parents=True)
        self.bin.write_bytes(b"SYNTHETIC_BINARY_NOT_SOUNDHACK")
        self.pin = hashlib.sha256(self.bin.read_bytes()).hexdigest()
        self.summary = self.root / "SH20-summary.json"
        self.summary.write_text(json.dumps({
            "status":"SH20_OFFICIAL_APP_REPLAY_STATIC_PASS",
            "verified_sha256":self.pin,
            "original_zip_sha256":gate.PIN_SH20_ZIP,
            "bundle_files":8,
            "nlist_import_count":393,
        }))
        self.parser = self.root / "macho_audit.py"
        self.parser.write_text("# mock parser -- deliberately not a Mach-O decoder\n")
        self.parser_pin = gate.git_blob(self.parser)
        self.sysroot = self.root / "sysroot"
        self.sysroot.mkdir()
        self.libA = "/System/Library/Frameworks/Carbon.framework/Versions/A/Carbon"
        self.libB = "/System/Library/Frameworks/QuickTime.framework/Versions/A/QuickTime"
        self.libC = "/usr/lib/libSystem.B.dylib"
        for lib in [self.libA,self.libB,self.libC]:
            p = self.sysroot / lib.lstrip("/")
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(b"DUMMY_PROVIDER_NO_MACHO")
        self.con = self.consumer()
        self.a = self.provider(self.libA, {"_Direct", "_Elsewhere"})
        self.b = self.provider(self.libB, {"_QuickTime"})
        self.c = self.provider(self.libC, {"_C"})
        self.providers={self.libA:self.a,self.libB:self.b,self.libC:self.c}

    def provider(self, name, names, **extra):
        return dict(install_name_requested=name, status="I386_PROVIDER_PARSED",
                    candidate_id=name, name_identity="EXACT",
                    nlist_defined=set(names), nlist_defined_count=len(names),
                    has_symtab=True,dyld_info=False, **extra)

    def imp(self, sym, lib=None, *, lookup="library", weak=False, common=False, weak_ref=False):
        return dict(name=sym, library_name=lib, lookup=lookup, weak_import=weak,
                    common_or_prebound=common, reference_to_weak=weak_ref)

    def consumer(self):
        return dict(arch="i386", filetype=2,bits=32,
                    sha256=self.pin, fat_slices=[{"arch":"ppc"},{"arch":"i386"}],
                    imports_nlist=["_Fake%03d"%i for i in range(393)],
                    imports_detail=[],
                    dylibs=[{"name":self.libA,"kind":"load"},
                            {"name":self.libB,"kind":"load"},
                            {"name":self.libC,"kind":"load"}],
                    has_dyld_info=False,two_level_namespace=True)

    def pins(self):
        return patch.multiple(gate,PIN_ORIGINAL=self.pin,PIN_PARSER_GIT_BLOB=self.parser_pin)

    def test_original_pins_verified(self):
        with self.pins():
            gate.validate_bundle(self.app, self.summary, self.parser)

    def test_mismatched_app_refused(self):
        with self.assertRaisesRegex(gate.Blocked,"SHA-256 mismatch"):
            gate.validate_bundle(self.app, self.summary, self.parser)

    def test_wrong_summary_hash_refused(self):
        self.summary.write_text(json.dumps({"status":"SH20_OFFICIAL_APP_REPLAY_STATIC_PASS"}))
        with self.pins(), self.assertRaisesRegex(gate.Blocked,"SH20 real-app evidence"):
            gate.validate_bundle(self.app,self.summary,self.parser)

    def test_modified_parser_refused(self):
        self.parser.write_text("# altered parser\n")
        with self.pins(), self.assertRaisesRegex(gate.Blocked,"Git blob differs"):
            gate.validate_bundle(self.app,self.summary,self.parser)

    def test_provider_rejects_escape_symlink(self):
        other = self.root / "outside"; other.write_bytes(b"X")
        path = self.sysroot / "usr/lib/escape.dylib"
        path.symlink_to(other)
        result = gate.provider_record("/usr/lib/escape.dylib",self.sysroot,types.SimpleNamespace())
        self.assertEqual(result["status"],"SYMLINK_ESCAPE_BLOCKED")

    def test_provider_missing(self):
        result=gate.provider_record("/usr/lib/missing.dylib",self.sysroot,types.SimpleNamespace())
        self.assertEqual(result["status"],"PROVIDER_NOT_A_FILE")

    def test_provider_rejects_non_absolute_load(self):
        result=gate.provider_record("@rpath/abc",self.sysroot,types.SimpleNamespace())
        self.assertEqual(result["status"],"NON_ABSOLUTE_INSTALL_NAME")

    def test_provider_parses_i386_without_reattribution(self):
        m=types.SimpleNamespace(inspect=lambda path,arch:dict(self.a,arch="i386",bits=32,
               filetype=6,exports_nlist=["_Direct"], sha256="a"*64,
               dylibs=[],has_symtab=True,has_dyld_info=False,symbol_caveats=[],install_name=self.libA),
               InvalidMachO=ValueError)
        result=gate.provider_record(self.libA,self.sysroot,m)
        self.assertEqual(result["status"],"I386_PROVIDER_PARSED")
        self.assertEqual(result["nlist_defined"],{"_Direct"})
        self.assertEqual(result["name_identity"],"EXACT")

    def test_provider_rejects_host_elf_not_macho(self):
        m=types.SimpleNamespace(inspect=lambda path,arch: (_ for _ in ()).throw(ValueError("not Mach-O")),
               InvalidMachO=ValueError)
        result=gate.provider_record(self.libA,self.sysroot,m)
        self.assertEqual(result["status"],"I386_MACHO_NOT_INSPECTABLE")

    def test_name_in_direct_provider(self):
        status, other=gate.classify_import(self.imp("_Direct",self.libA),self.providers)
        self.assertEqual((status,other),("NAME_DIRECT_IN_EXPECTED_LIBRARY",[]))

    def test_name_missing_direct_provider(self):
        status,_=gate.classify_import(self.imp("_Unknown",self.libA),self.providers)
        self.assertEqual(status,"NAME_NOT_IN_DIRECT_PROVIDER_NLIST")

    def test_name_only_other_provider_is_not_direct_resolution(self):
        status,other=gate.classify_import(self.imp("_QuickTime",self.libA),self.providers)
        self.assertEqual(status,"NAME_ONLY_IN_OTHER_LOADED_LIBRARY")
        self.assertEqual(other,[self.libB])

    def test_name_in_provider_but_identity_differs(self):
        providers={self.libA:dict(self.a,name_identity="MISMATCH_OR_ABSENT")}
        status,_=gate.classify_import(self.imp("_Direct",self.libA),providers)
        self.assertEqual(status,"NAME_PRESENT_IDENTITY_UNVERIFIED")

    def test_ordinal_unknown_is_not_mislabeled_missing(self):
        status,_=gate.classify_import(self.imp("_Unknown",lookup="dynamic_lookup"),self.providers)
        self.assertEqual(status,"INCONCLUSIVE_SPECIAL_LOOKUP")

    def test_nonstandard_reference_remains_inconclusive(self):
        status,_=gate.classify_import(self.imp("_Direct",self.libA,common=True),self.providers)
        self.assertEqual(status,"INCONCLUSIVE_NONSTANDARD_REFERENCE")

    def test_provider_missing_remains_inconclusive(self):
        p=dict(self.a,status="PROVIDER_NOT_A_FILE")
        status,_=gate.classify_import(self.imp("_Direct",self.libA),{self.libA:p})
        self.assertEqual(status,"INCONCLUSIVE_PROVIDER_UNAVAILABLE")

    def test_report_records_are_not_collapsed(self):
        c=dict(self.con,imports_detail=[self.imp("_Direct",self.libA),self.imp("_Direct",self.libA),self.imp("_QuickTime",self.libA)])
        with patch.object(gate,"PIN_ORIGINAL",self.pin):
            report=gate.analyze(c,self.providers)
        self.assertEqual(report["app_nlist_ordinal_records"],3)
        self.assertEqual(report["classification_counts"],{"NAME_DIRECT_IN_EXPECTED_LIBRARY":2,"NAME_ONLY_IN_OTHER_LOADED_LIBRARY":1})
        self.assertFalse(report["guest_executed"])

    def test_wrong_architecture_refused(self):
        c=dict(self.con,arch="ppc")
        with patch.object(gate,"PIN_ORIGINAL",self.pin), self.assertRaisesRegex(gate.Blocked,"consumer Mach-O"):
            gate.analyze(c,self.providers)

    def test_wrong_import_count_refused(self):
        c=dict(self.con,imports_nlist=["_A"])
        with patch.object(gate,"PIN_ORIGINAL",self.pin), self.assertRaisesRegex(gate.Blocked,"imported symbol count"):
            gate.analyze(c,self.providers)

    def test_cli_full_positive_synthetic_seven_providers(self):
        libs = [
          "/System/Library/Frameworks/Carbon.framework/Versions/A/Carbon",
          "/System/Library/Frameworks/QuickTime.framework/Versions/A/QuickTime",
          "/System/Library/Frameworks/CoreAudio.framework/Versions/A/CoreAudio",
          "/System/Library/Frameworks/AudioToolbox.framework/Versions/A/AudioToolbox",
          "/System/Library/Frameworks/AudioUnit.framework/Versions/A/AudioUnit",
          "/usr/lib/libgcc_s.1.dylib",
          "/usr/lib/libSystem.B.dylib",
        ]
        for lib in libs:
            p = self.sysroot / lib.lstrip("/")
            p.parent.mkdir(parents=True,exist_ok=True)
            if not p.exists(): p.write_bytes(b"SYNTHETIC_DYLIB_NOT_MACOS")
        fake_consumer = dict(self.con,
            dylibs=[{"kind":"load","name":n} for n in libs],
            imports_nlist=["_Sym%03d"%i for i in range(393)],
            imports_detail=[self.imp("_Sym%03d"%i,libs[i%7]) for i in range(393)])
        def inspect(path,arch):
            if path.name == "SoundHack":
                return fake_consumer
            for idx,lib in enumerate(libs):
                if str(path).endswith(lib):
                    exports=["_Sym%03d"%i for i in range(393) if i%7==idx]
                    return {"filetype":6,"bits":32,"exports_nlist":exports,
                            "install_name":lib,"sha256":"a"*64,"dylibs":[],
                            "has_dyld_info":False,"has_symtab":True,"symbol_caveats":[]}
            raise ValueError("unexpected provider in test")
        fake=types.SimpleNamespace(inspect=inspect,InvalidMachO=ValueError)
        out = self.root / "SH21-positive.json"
        with self.pins(),patch.dict(sys.modules,{"macho_audit":fake}),contextlib.redirect_stdout(io.StringIO()):
            rc=gate.main(["--app",str(self.app),"--summary",str(self.summary),
                          "--sysroot",str(self.sysroot),"--parser",str(self.parser),"--output",str(out)])
        self.assertEqual(rc,0)
        result=json.loads(out.read_text())
        self.assertEqual(result["status"],"SH21_STATIC_IMPORT_CLASSIFIED")
        self.assertEqual(result["classification_counts"],{"NAME_DIRECT_IN_EXPECTED_LIBRARY":393})
        self.assertEqual(result["provider_i386_macho_parsed"],7)
        self.assertFalse(result["guest_executed"])
        self.assertEqual(len(result["imports"]),393)

    def test_existing_output_not_overwritten(self):
        out=self.root/"existing.json"
        out.write_text("DO_NOT_OVERWRITE")
        with contextlib.redirect_stdout(io.StringIO()):
            rc=gate.main(["--app",str(self.app),"--summary",str(self.summary),"--sysroot",str(self.sysroot),"--parser",str(self.parser),"--output",str(out)])
        self.assertEqual(rc,3)
        self.assertEqual(out.read_text(),"DO_NOT_OVERWRITE")

    def test_cli_synthetic_without_software_execution(self):
        out=self.root/"SH21-report.json"
        fake_consumer=dict(self.con,imports_detail=[self.imp("_Direct",self.libA)])
        def inspect(path,arch):
            if path.name=="SoundHack":return fake_consumer
            names={self.libA:{"_Direct"},self.libB:{"_QuickTime"},self.libC:{"_C"}}
            chosen=next((name for name in names if str(path).endswith(name)),None)
            if chosen is None:raise ValueError("unexpected provider")
            p=dict(self.provider(chosen,names[chosen]),filetype=6,bits=32,
                   exports_nlist=sorted(names[chosen]),sha256="b"*64,dylibs=[],has_dyld_info=False,
                   has_symtab=True,symbol_caveats=[],install_name=chosen)
            return p
        fake_macho=types.SimpleNamespace(inspect=inspect,InvalidMachO=ValueError)
        with self.pins(),patch.dict(sys.modules,{"macho_audit":fake_macho}), contextlib.redirect_stdout(io.StringIO()):
            rc=gate.main(["--app",str(self.app),"--summary",str(self.summary),"--sysroot",str(self.sysroot),"--parser",str(self.parser),"--output",str(out)])
        self.assertEqual(rc,3)  # intentionally 3 libs not historical 7, negative gate
        self.assertFalse(out.exists())


if __name__=="__main__":unittest.main()
