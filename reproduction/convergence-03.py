#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""CONVERGENCE-03: prepare and test a source-only candidate; no runtime changes.
Inputs: the local CONVERGENCE-01 and successful CONVERGENCE-02 workspaces.
Public sources are pinned to immutable commits and checked by Git blob SHA.
The native tests use explicit host-only adapters, not Darwin ABI qualification.
No private application source, binary, or log is published by this script.
"""
import base64
import difflib
import hashlib
import os
from pathlib import Path
import platform
import re
import shutil
import signal
import subprocess as sp
import sys
import tempfile
import time
import urllib.request

ROOT = Path.home() / "d4wrling-work/validation"
WIN = Path("/mnt/c/_Atelier_IA/D4rling")
FORK = "294496b9b34dc9d2bffee45991462d7b915e4f25"
UP = "dd60fabbeb18cb8a30765c69790660a86ee21ae9"
BASE = "36536a662356001194a7cfad2b42b509003d6bd8"
C = "src/frameworks/CoreServices/src/CarbonCore/"
I = "src/frameworks/CoreServices/include/CarbonCore/"
O = "src/frameworks/CoreServices/src/OSServices/"
A = "src/CoreAudio/AudioToolbox/"
MM, MH, ME = C+"MacMemory.cpp", I+"MacMemory.h", I+"MacErrors.h"
PCM = A+"PCMConverter.cpp"
WS, CM = O+"WSMethodInvocation.c", O+"CMakeLists.txt"
RM = [C+"Resources.cpp", C+"ResourcesImpl.cpp", C+"ResourcesImpl.h"]
ALLOWED = set(RM+[PCM, WS, CM])
PINS = {
    ("F",MM):"26dfea4803ad1499a542f8843862f8998dc5f292",
    ("U",MM):"a4d1c9fa6fec556e7680ba80598e672bd7ab39bd",
    ("F",MH):"91be5171aee4910f7910f465a1da96519127a96e",
    ("U",MH):"cfa65b6bf6b723302963f8495f50dd96cec6ae87",
    ("U",ME):"fef87e7c791c880a51a7a304c0c5c7d9e455141d",
    ("U",PCM):"8d5ea7c303c28460c2ce0fef07c2ad710e5bd6c8",
    ("U",CM):"5a723d7fdea951b0f02b430dfdce253a55171997",
    ("F",WS):"f7a79b8733440e52a3bee64d4fc08151ec887b0b",
    ("U",RM[0]):"ce0753e18c199f91737e70980fb4b5fb2ace0115",
    ("U",RM[1]):"4811fb489b48441968d6a763ad195e35062740ca",
    ("U",RM[2]):"702cee0c20bf5a7ef23fa77a19f98c6f2721127a",
    ("F",RM[1]):"30714d701c18491c806f4a1c45d6c4cf902fd53d",
    ("F",RM[2]):"08eca11a823b4549dfc3f40229d9f729938ba385",
}
ENV = {k:v for k,v in os.environ.items() if not k.startswith("GIT_")}
ENV.update(GIT_NO_LAZY_FETCH="1", GIT_OPTIONAL_LOCKS="0",
           GIT_TERMINAL_PROMPT="0", GIT_CONFIG_NOSYSTEM="1",
           GIT_CONFIG_GLOBAL="/dev/null", LC_ALL="C")
W = p1 = p2 = None
messages, failures, changes, cache = [], [], {}, {}
network = 0
protected = {}
before = {}
review = {}
rc = 2

def emit(s):
    messages.append(s)
    print(s, flush=True)
    if W:
        with (W/"REPORT.txt").open("a", encoding="utf-8") as f:
            f.write(s+"\n")

def step(n, title):
    print(f"\033]0;D4RLING CONVERGENCE-03 {n}/6 {title}\007",
          end="", flush=True)
    emit(f"[{n}/6] {title}")

def progress(i, n):
    k = 24*i//n
    print(f"[{'#'*k}{'.'*(24-k)}] {i}/{n}", flush=True)

def need(ok, reason):
    if not ok:
        raise ValueError(reason)

def short(e):
    return str(e)[:140] if isinstance(e, ValueError) else type(e).__name__

def put(p, b):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(b)

def sha(b):
    return hashlib.sha256(b).hexdigest()

def filehash(p):
    with p.open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()

def blob(b):
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()

def manifest(p):
    result = {}
    for line in p.read_text().splitlines():
        h, name = line.split("  ", 1)
        need(re.fullmatch(r"[0-9a-f]{64}",h) and name not in result,
             "MANIFEST_FORMAT")
        result[name] = h
    return result

def previous(prefix, expected):
    for p in sorted(ROOT.glob(prefix+"-*"), reverse=True)[:30]:
        try:
            d = dict(x.split("=",1) for x in
                     (p/"REPORT.txt").read_text().splitlines() if "=" in x)
            if all(d.get(k)==v for k,v in expected.items()):
                return p, d
        except OSError:
            pass
    raise ValueError(prefix+"_SUCCESS_NOT_FOUND")

def source(tag, path):
    global network
    key = (tag,path)
    if key in cache:
        return cache[key]
    h = PINS[key]
    opts = [p1/"sources"/("FORK" if tag=="F" else "UP")/path,
            p2/"extra"/tag/path]
    b = None
    for p in opts:
        if p.is_file() and p.stat().st_size <= 1024*1024:
            v = p.read_bytes()
            if blob(v)==h:
                b = v
                break
    if b is None:
        repo, ref = ("fr4nck/d4rling",FORK) if tag=="F" else ("darlinghq/darling",UP)
        need(network < 1024*1024, "NETWORK_BUDGET")
        url = f"https://raw.githubusercontent.com/{repo}/{ref}/{path}"
        emit("READ_PUBLIC "+tag+" "+Path(path).name)
        with urllib.request.urlopen(url, timeout=15) as f:
            b = f.read(1024*1024-network+1)
        network += len(b)
        need(network <= 1024*1024, "NETWORK_BUDGET")
    need(blob(b)==h, "SOURCE_PIN_MISMATCH "+tag+" "+Path(path).name)
    cache[key] = b
    put(W/"sources"/tag/path,b)
    return b

def run(name, args, cwd, limit=45):
    log = W/"logs"/(name+".log")
    log.parent.mkdir(exist_ok=True)
    env = dict(ENV, GIT_CEILING_DIRECTORIES=str(cwd.parent))
    with log.open("wb") as f:
        p = sp.Popen(args, cwd=cwd, env=env, stdout=f, stderr=sp.STDOUT,
                     start_new_session=True)
        start = time.monotonic()
        try:
            while True:
                try:
                    return p.wait(timeout=2)
                except sp.TimeoutExpired:
                    elapsed = time.monotonic()-start
                    print(f"  {name}: actif {int(elapsed)} s",flush=True)
                    if elapsed >= limit:
                        return 124
        finally:
            if p.poll() is None:
                try:
                    os.killpg(p.pid,signal.SIGKILL)
                except ProcessLookupError:
                    pass
                p.wait()

def apply_patch(name, patch, originals):
    stage = W/"stage"/name
    stage.mkdir(parents=True)
    for path,b in originals.items():
        if b is not None:
            put(stage/path,b)
    pf = W/(name+".patch")
    put(pf,patch)
    for mode in (["--check"],[]):
        status = run(name+("_check" if mode else "_apply"),
                     ["git","-c","protocol.allow=never","apply",
                      "--whitespace=nowarn",*mode,str(pf)],stage)
        need(status==0,"PATCH_APPLY_FAILED "+name)
    return {p:(stage/p).read_bytes() for p in originals}

def record(items):
    for p,(a,b) in items.items():
        need(p not in changes and a!=b,"EMPTY_OR_DUPLICATE "+Path(p).name)
    for p,(a,b) in items.items():
        put(W/"candidate"/p,b)
        changes[p]=(a,b)

def delta(items):
    out = []
    for p,(a,b) in sorted(items.items()):
        x = (a or b"").decode().splitlines(keepends=True)
        y = b.decode().splitlines(keepends=True)
        need(all(s.endswith("\n") for s in x+y),"SOURCE_FINAL_NEWLINE")
        out.append(f"diff --git a/{p} b/{p}\n"
                   +("new file mode 100644\n" if a is None else "")
                   +"".join(difflib.unified_diff(
                       x,y,"/dev/null" if a is None else "a/"+p,"b/"+p)))
    return "".join(out).encode()

def restore_previous():
    patch = (p2/"REVIEW-ONLY.diff").read_bytes()
    need(len(patch)<1024*1024,"PREVIOUS_PATCH_SIZE")
    need(manifest(p2/"SHA256SUMS").get("REVIEW-ONLY.diff")==sha(patch),
         "PREVIOUS_PATCH_SHA")
    sections = {}
    for s in re.split(r"(?=^diff --git )",patch.decode(),flags=re.M):
        if not s:
            continue
        m = re.match(r"^diff --git a/(\S+) b/(\S+)\n",s)
        need(m and m[1]==m[2] and m[1] in ALLOWED and m[1] not in sections,
             "PREVIOUS_PATCH_PATH")
        p = m[1]
        header = s.split("\n@@ ",1)[0]
        expected = "--- "+("/dev/null" if p==WS else "a/"+p)+"\n+++ b/"+p
        need(expected in header and not re.search(
            r"^(rename |copy |deleted file|GIT binary patch|old mode|new mode)",
            header,re.M),"PREVIOUS_PATCH_HEADER")
        sections[p] = s
    return sections

def prepare_group(name, paths, sections):
    need(set(paths)<=sections.keys(),"PREVIOUS_GROUP_MISSING")
    a = {p:None if p==WS else source("U",p) for p in paths}
    b = apply_patch(name,"".join(sections[p] for p in paths).encode(),a)
    if name=="WSKEY":
        need(b[WS]==source("F",WS)
             and b[CM]==a[CM].replace(b"\t\tPower.c\n",
                 b"\t\tPower.c\n\t\tWSMethodInvocation.c\n",1),"WSKEY_CONTRACT")
    if name=="RESOURCE":
        need(b[RM[1]]==source("F",RM[1])
             and b[RM[2]]==source("F",RM[2]),"RESOURCE_FAMILY")
        s=b[RM[0]].decode()
        need(len(re.findall(r"^ResFileRefNum HomeResFile\(",s,re.M))==1
             and all(x in s for x in (
                 "ensureAppResourceFile();","FSGetResourceForkName(&forkName);",
                 "owner->readPartial(","owner->writePartial(",
                 "owner->sizeOnDisk(","Resources::shouldLoad()")),
             "RESOURCE_CONTRACT")
    if name=="PCM":
        old = a[PCM].decode()
        anchor = ("\tconst UInt32 frames = inInputDataSize / m_src.frameBytes;\n\n"
                  "\tif (*ioOutputDataSize < frames * m_dst.frameBytes)\n"
                  "\t\treturn kAudioConverterErr_InvalidInputSize;")
        replacement = (
            "\tif (!m_src.frameBytes || !m_dst.frameBytes || "
            "inInputDataSize % m_src.frameBytes)\n"
            "\t\treturn kAudioConverterErr_InvalidInputSize;\n\n"
            "\tconst UInt32 frames = inInputDataSize / m_src.frameBytes;\n"
            "\tconst UInt64 required = UInt64(frames) * m_dst.frameBytes;\n"
            "\tif (required > *ioOutputDataSize)\n"
            "\t\treturn kAudioConverterErr_InvalidInputSize;")
        tail = "\t*ioOutputDataSize = frames * m_dst.frameBytes;"
        need(old.count(anchor)==1 and old.count(tail)==1,"PCM_ANCHOR")
        expected = old.replace(anchor,replacement,1).replace(
            tail,"\t*ioOutputDataSize = static_cast<UInt32>(required);",1)
        need(b[PCM]==expected.encode(),"PCM_CONTRACT")
    record({p:(a[p],b[p]) for p in paths})

MMTEST = r"""
#include <CarbonCore/MacMemory.h>
#include <CarbonCore/MacErrors.h>
#include <cstring>
#include <cstdio>
#include <cstdint>
int main(){
    Handle h=NewHandle(7);
    if(!h||!*h) return 3;
    memcpy(*h,"abcdefg",7);
    bool basic=GetHandleSize(h)==7;
    SetHandleSize(h,3);
    basic=basic&&*h&&GetHandleSize(h)==3&&!memcmp(*h,"abc",3);
    HLock(h); EmptyHandle(h);
#if CANDIDATE
    bool err=MemError()==memPurErr;
#endif
    bool locked=*h&&GetHandleSize(h)==3&&!memcmp(*h,"abc",3);
    HUnlock(h); EmptyHandle(h);
    basic=basic&&!*h;
    ReallocateHandle(h,4);
    basic=basic&&*h&&GetHandleSize(h)==4;
    DisposeHandle(h);
#if CANDIDATE
    bool invalid=GetHandleSize(reinterpret_cast<Handle>(uintptr_t(1)))==0
                 &&MemError()==memWZErr;
    basic=basic&&err&&invalid;
#endif
    printf("BASIC=%d LOCKED_PURGE=%d\n",int(basic),int(locked));
    return !basic?3:locked?0:1;
}
"""
PCM_PREFIX = r"""
#include <cstdint>
#include <vector>
#include <cstdio>
using UInt32=uint32_t;
using UInt64=uint64_t;
using OSStatus=int;
constexpr int noErr=0,paramErr=-50,kAudioConverterErr_InvalidInputSize=-1;
struct PCMConverter {
    struct Format { UInt32 frameBytes,buffers; };
    Format m_src{2,1},m_dst{4,1};
    bool m_resample=false;
    unsigned calls=0;
    void convertFrames(const std::vector<uint8_t*>&,UInt32,
        const std::vector<uint8_t*>&,UInt32,UInt32){++calls;}
    OSStatus convertBuffer(UInt32,const void*,UInt32*,void*);
};
"""
PCM_TEST = r"""
int main(){
    PCMConverter c; char b[16]{}; UInt32 n=16;
    bool basic=c.convertBuffer(8,b,&n,b)==noErr&&n==16&&c.calls==1;
    c.calls=0; n=16;
    bool partial=c.convertBuffer(3,b,&n,b)==kAudioConverterErr_InvalidInputSize
                 &&n==16&&!c.calls;
    c.calls=0; n=1; c.m_src.frameBytes=1; c.m_dst.frameBytes=4;
    bool overflow=c.convertBuffer(0x40000000u,b,&n,b)==kAudioConverterErr_InvalidInputSize
                  &&n==1&&!c.calls;
    printf("BASIC=%d PARTIAL=%d OVERFLOW=%d\n",int(basic),int(partial),int(overflow));
    return !basic?3:partial&&overflow?0:!partial&&!overflow?1:3;
}
"""

def native(kind, bits, compiler):
    need(compiler is not None,"CXX_MISSING")
    need((MM if kind=="MEMORY" else PCM) in changes,"CANDIDATE_MISSING")
    codes=[]
    for t in ("U","F"):
        name=f"{kind}_{bits}_{t}"
        d=W/"native"/name
        d.mkdir(parents=True)
        if kind=="MEMORY":
            inc=d/"include"
            put(inc/"MacTypes.h",b"""#pragma once
#include <stdint.h>
typedef long Size;
typedef char* Ptr;
typedef Ptr* Handle;
typedef int16_t OSErr;
typedef int32_t OSStatus;
enum {noErr=0};
""")
            put(inc/"CoreFoundation/CFBase.h",b"#pragma once\n#include <MacTypes.h>\n")
            put(inc/"malloc/malloc.h",b"""#pragma once
#include <malloc.h>
static inline size_t malloc_size(const void* p){
    return malloc_usable_size(const_cast<void*>(p));
}
""")
            put(inc/"CarbonCore/MacMemory.h",source(t,MH))
            put(inc/"CarbonCore/MacErrors.h",source("U",ME))
            put(d/"impl.cpp",source(t,MM))
            put(d/"test.cpp",MMTEST.encode())
            args=["-I"+str(inc),"-DCANDIDATE="+str(int(t=="F")),
                  "impl.cpp","test.cpp"]
        else:
            src=changes[PCM][int(t=="F")].decode()
            m=re.search(r"^OSStatus PCMConverter::convertBuffer\(.*?\n\}",src,re.M|re.S)
            need(m,"PCM_METHOD_MISSING")
            put(d/"test.cpp",(PCM_PREFIX+m[0]+"\n"+PCM_TEST).encode())
            args=["test.cpp"]
        status=run(name+"_build",[compiler,"-m"+str(bits),"-std=c++17",
                                  "-pthread","-O0",*args,"-o","probe"],d)
        if status:
            emit(name+"_BUILD_RC="+str(status))
            codes.append(None)
            continue
        status=run(name+"_test",[str(d/"probe")],d,15)
        codes.append(status)
        emit(name+"_RC="+str(status))
        for s in (W/"logs"/(name+"_test.log")).read_text(errors="replace").splitlines():
            if s.startswith("BASIC="):
                emit(name+" "+s)
    return ("PASS_DIFFERENTIAL" if codes==[1,0] else
            "BLOCKED_BUILD" if None in codes else "FAIL_DIFFERENTIAL")

def independently(name, fn):
    try:
        fn()
        emit(name+"=PASS")
    except Exception as e:
        failures.append(name)
        emit(name+"=BLOCKED_"+short(e))

def locate_protected():
    # Identify the exact two qualified binaries by local caller-supplied hashes.
    # Do not publish machine-specific paths or binary fingerprints in Git.
    need(len(sys.argv)==3 and all(re.fullmatch(r"[0-9a-f]{64}",x)
                                for x in sys.argv[1:]),"PROTECTED_HASH_ARGS")
    wanted=set(sys.argv[1:])
    need(len(wanted)==2,"DISTINCT_PROTECTED_HASHES_REQUIRED")
    files=sorted(ROOT.glob("sh36r2-*/sh44-*/SoundHack.app/Contents/MacOS/SoundHack"))
    need(len(files)<=100,"PROTECTED_SCAN_BUDGET")
    total=0
    for i,p in enumerate(files,1):
        if p.is_file():
            total+=p.stat().st_size
            need(total<=256*1024*1024,"PROTECTED_BYTE_BUDGET")
            h=filehash(p)
            if h in wanted:
                protected[str(p)]=h
        progress(i,max(1,len(files)))
    need(set(protected.values())==wanted,"PROTECTED_BINARIES_NOT_FOUND")
    emit("PROTECTED_BINARIES="+str(len(protected)))
    # Preserve recovered CP27 source copies, never export them.
    cp=p2/"cp27-private"
    files=sorted(cp.glob("*"))
    need(len(files)==6 and all(p.is_file() and p.stat().st_size<=4*1024*1024
                              for p in files),"CP27_SOURCES_MISSING")
    for p in files:
        protected[str(p)]=filehash(p)
    before.update(protected)
    emit("CP27_LOCAL_SOURCES=6")
    emit("CP27_PROVENANCE=REUSED_NOT_REQUALIFIED")

def main():
    global W,p1,p2
    step(1,"Prevol et reprise")
    need("microsoft" in platform.release().lower(),"NOT_WSL")
    need("AMD Ryzen 7 5700X" in Path("/proc/cpuinfo").read_text(),"HOST_NOT_5700X")
    need(ROOT.is_dir() and shutil.which("git"),"ROOT_OR_GIT_MISSING")
    W=Path(tempfile.mkdtemp(prefix="CONVERGENCE-03-"+time.strftime("%Y%m%d-%H%M%S")+"-",
                            dir=ROOT))
    put(W/"REPORT.txt",("\n".join(messages)+"\n").encode())
    # Keep the exact launcher for AGT-015 reproduction.
    shutil.copyfile(Path(__file__).resolve(),W/"runner.py")
    emit("HOST_5700X=PASS")
    emit("UP_SHA="+UP)
    p1,_=previous("CONVERGENCE-01",{
        "BASE_SHA":BASE,"FORK_SHA":FORK,"UP_SHA":UP,"EXIT":"0",
        "RESULT":"SOURCE_TRIAGE_COMPLETE_REVIEW_REQUIRED"})
    p2,d2=previous("CONVERGENCE-02",{
        "EXIT":"0","RESULT":"CANDIDATES_PREPARED_SEMANTIC_REVIEW_REQUIRED"})
    emit("CONVERGENCE_01=REUSED")
    emit("CONVERGENCE_02=REUSED")
    step(2,"Protection des preuves")
    locate_protected()
    sections=restore_previous()
    emit("PREVIOUS_PATCH_SHA=PASS")
    step(3,"Candidats sources")
    groups=[("WSKEY",[CM,WS]),("RESOURCE",RM),("PCM",[PCM])]
    for i,(name,paths) in enumerate(groups,1):
        independently(name,lambda n=name,p=paths:prepare_group(n,p,sections))
        progress(i,4)
    def memory():
        record({p:(source("U",p),source("F",p)) for p in (MM,MH)})
    independently("MEMORY_SOURCE_CANDIDATE",memory)
    progress(4,4)
    step(4,"Tests natifs differentiels")
    compiler=shutil.which("g++") or shutil.which("clang++")
    for i,(bits,kind) in enumerate([(32,"MEMORY"),(32,"PCM"),
                                   (64,"MEMORY"),(64,"PCM")],1):
        try:
            result=native(kind,bits,compiler)
        except Exception as e:
            result="BLOCKED_"+short(e)
        emit(f"{kind}_NATIVE_{bits}="+result)
        if result!="PASS_DIFFERENTIAL":
            failures.append(kind+str(bits))
        progress(i,4)
    step(5,"Patch et reproductibilite")
    def combine():
        need(changes,"NO_CANDIDATE")
        patch=delta(changes)
        put(W/"CANDIDATE.patch",patch)
        out=apply_patch("combined",patch,{p:a for p,(a,b) in changes.items()})
        need(all(out[p]==b for p,(a,b) in changes.items()),"ROUNDTRIP")
        emit("CANDIDATE_SHA256="+sha(patch))
    independently("PATCH_ROUNDTRIP",combine)
    emit("CANDIDATE_FILES="+str(len(changes)))
    emit("REMOTE_BYTES="+str(network))
    emit("MEMORY_ADAPTER=HOST_ONLY")
    emit("FOREIGN_HANDLE_COMPATIBILITY=NOT_QUALIFIED")
    emit("PCM_TEST=EXACT_METHOD_TEST_ONLY_CONVERTFRAMES")
    emit("AUDIOCONVERTER_FALLBACK=REVIEW_REQUIRED")
    emit("QUICKTIME_PCM_PORT=DEFERRED_NO_WRITE")
    return 2 if failures else 0

def finish(status):
    step(6,"Integrite et livraison")
    if before:
        ok=True
        for p,h in before.items():
            try:
                ok=(filehash(Path(p))==h) and ok
            except OSError:
                ok=False
        emit("PROTECTED_INPUTS_UNCHANGED="+("PASS" if ok else "FAIL"))
        if not ok and status==0:
            status=2
    else:
        emit("PROTECTED_INPUTS_UNCHANGED=NOT_VERIFIED")
    emit("MASTER_WRITES=NO")
    emit("RUNTIME_REBUILT=NO")
    emit("GUEST_QUALIFICATION=NOT_RUN")
    emit("PRODUCTION_READY=NO")
    emit("RESULT="+("SOURCE_CANDIDATE_NATIVE_TESTS_PASS_REVIEW_REQUIRED"
                    if status==0 else "PARTIAL_OR_BLOCKED"))
    emit("EXIT="+str(status))
    dest=None
    export="NOT_RUN"
    if W:
        try:
            put(W/"MATRIX.tsv",("PATH\tUP_BLOB\tCANDIDATE_BLOB\n"
                +"".join(p+"\t"+(blob(a) if a is not None else "-")+"\t"+blob(b)+"\n"
                         for p,(a,b) in sorted(changes.items()))).encode())
            names=[n for n in ("CANDIDATE.patch","MATRIX.tsv","runner.py")
                   if (W/n).is_file()]
            put(W/"SHA256SUMS",("".join(filehash(W/n)+"  "+n+"\n" for n in names)).encode())
            dest=WIN/W.name
            dest.mkdir()
            for n in names+["SHA256SUMS","REPORT.txt"]:
                shutil.copyfile(W/n,dest/n)
            export="PASS"
        except OSError:
            export="FAIL"
    emit("WINDOWS_EXPORT="+export)
    if export=="PASS":
        try:
            shutil.copyfile(W/"REPORT.txt",dest/"REPORT.txt")
        except OSError:
            emit("WINDOWS_REPORT_UPDATE=FAIL")
    report=("\n".join(messages)+"\n").encode()
    token=base64.b64encode(report)
    clip="NOT_AVAILABLE"
    ps=shutil.which("powershell.exe")
    if ps:
        cmd=('$ErrorActionPreference="Stop"; '
             '$s=[Text.Encoding]::UTF8.GetString([Convert]::FromBase64String([Console]::In.ReadToEnd())); '
             'Set-Clipboard -Value $s; '
             '[Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes([string](Get-Clipboard -Raw)))')
        try:
            r=sp.run([ps,"-NoProfile","-NonInteractive","-Command",cmd],
                     input=token,stdout=sp.PIPE,stderr=sp.PIPE,timeout=25)
            clip="PASS" if r.returncode==0 and r.stdout.strip()==token else "MISMATCH_OR_FAIL"
        except (OSError,sp.TimeoutExpired):
            clip="FAIL"
    elif shutil.which("clip.exe"):
        try:
            clip="COPIED_NOT_VERIFIED" if sp.run(["clip.exe"],input=report,timeout=15).returncode==0 else "FAIL"
        except (OSError,sp.TimeoutExpired):
            clip="FAIL"
    print("CLIPBOARD_READBACK="+clip,flush=True)
    if W:
        put(W/"DELIVERY.txt",f"CLIPBOARD_READBACK={clip}\nEXIT={status}\n".encode())
        print("LINUX_REPORT="+str(W/"REPORT.txt"),flush=True)
        if export=="PASS":
            try:
                shutil.copyfile(W/"DELIVERY.txt",dest/"DELIVERY.txt")
            except OSError:
                print("DELIVERY_EXPORT=FAIL",flush=True)
    print("\033]0;D4RLING CONVERGENCE-03 termine\007",end="",flush=True)
    return status

if __name__=="__main__":
    try:
        rc=main()
    except KeyboardInterrupt:
        rc=130
        emit("INTERRUPTED=YES")
    except Exception as e:
        emit("FATAL="+short(e))
    try:
        rc=finish(rc)
    except Exception as e:
        print("DELIVERY_BLOCKED="+type(e).__name__,flush=True)
    sys.exit(rc)
