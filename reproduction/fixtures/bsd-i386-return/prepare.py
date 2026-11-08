#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Materialize three available local Git blobs into a new independent test tree.

No clone, fetch, submodule update, build/install mutation or runtime launch.
"""
import argparse,hashlib,json,os,pathlib,shutil,subprocess

kit=pathlib.Path(__file__).resolve().parent
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--xnu',required=True,type=pathlib.Path,help='Existing local darling-xnu Git checkout')
parser.add_argument('--output',required=True,type=pathlib.Path,help='New destination; must not exist')
args=parser.parse_args()
manifest=json.loads((kit/'manifest.json').read_text())
revision=manifest['source_revision']
environment={**os.environ,'GIT_OPTIONAL_LOCKS':'0','GIT_NO_LAZY_FETCH':'1'}
patch=kit.parents[1]/'patches/bsd-i386-return-fa29287.patch'
assert hashlib.sha256(patch.read_bytes()).hexdigest()==manifest['patch_sha256']
if args.output.exists():
    parser.error('--output must name a new destination')
inputs={}
for name,info in manifest['source_files'].items():
    data=subprocess.check_output(['git','-C',str(args.xnu),'show',f'{revision}:{name}'],env=environment)
    assert hashlib.sha256(data).hexdigest()==info['original_sha256'],name
    inputs[name]=data
args.output.mkdir(parents=True)
output=args.output.resolve()
for tree in ['original','candidate']:
    for name,data in inputs.items():
        destination=output/tree/name
        destination.parent.mkdir(parents=True,exist_ok=True)
        destination.write_bytes(data)
subprocess.run(['git','apply','--check',str(patch)],cwd=output/'candidate',check=True,env=environment)
subprocess.run(['git','apply',str(patch)],cwd=output/'candidate',check=True,env=environment)
for name,info in manifest['source_files'].items():
    assert hashlib.sha256((output/'candidate'/name).read_bytes()).hexdigest()==info['candidate_sha256'],name
tests=output/'candidate/tests/bsd-i386-return'
tests.mkdir(parents=True)
for name in ['probe.c','fixture.S','run-tests.sh','run-private.sh']:
    shutil.copyfile(kit/name,tests/name)
(output/'PUBLIC-INPUTS.json').write_text(json.dumps(manifest,indent=2)+'\n')
print('PREPARE_SOURCE=PASS')
print(output)
