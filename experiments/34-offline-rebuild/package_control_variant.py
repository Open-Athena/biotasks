"""Build the candidate input archive only from verified reconstruction evidence."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import tarfile

from prepare_control_variant import prepare

ROOT=Path(__file__).resolve().parent

def load(name):
    return json.loads((ROOT/name).read_text())

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--original',type=Path,required=True)
    p.add_argument('--original-plan',type=Path,required=True)
    args=p.parse_args()
    image=load('macs-742-image-result-001.json')
    receipt=load('macs-742-image-readback-001.json')
    accounting=load('macs-742-image-accounting.json')
    assert accounting['state']=='succeeded' and accounting['exit_code']==0
    assert image['smoke_passed'] and image['verify_passed'] and image['cleanup_verified']
    assert receipt['result_record_verified'] and receipt['owned_containers_absent']
    assert receipt['archive_sha256']==accounting['output_archive']['sha256']
    assert receipt['retained_image_id']==image['retained_image_id']
    workspace=ROOT/'inputs-private/offline-controls'
    assert not workspace.exists(), 'Preserve existing package; validate it rather than recreate it'
    destination=workspace/'outputs/macs3-project__MACS/macs3-project__MACS-742'
    destination.parent.mkdir(parents=True)
    plan,manifest=prepare(args.original,args.original_plan,image['retained_image_id'],destination)
    for filename,data in [('offline-control-plan.json',plan),('offline-export-manifest.json',manifest)]:
        target=ROOT/filename
        assert not target.exists(), 'Never replace a recorded candidate manifest'
        target.write_text(json.dumps(data,indent=2)+'\n')
    archive=workspace/'original-tasks.tar.gz'
    with archive.open('wb') as raw,gzip.GzipFile(filename='',mode='wb',fileobj=raw,mtime=0) as stream,tarfile.open(fileobj=stream,mode='w|') as bundle:
        for file in sorted(destination.rglob('*')):
            if file.is_file():
                info=bundle.gettarinfo(str(file),arcname=str(file.relative_to(workspace)))
                assert info.isfile() and info.size<1024**2
                info.uid=info.gid=0;info.uname=info.gname='';info.mtime=0
                with file.open('rb') as source:bundle.addfile(info,source)
    # Independently read every published member and compare the candidate inventory.
    expected={f['path']:f for f in manifest['task_files']}
    with tarfile.open(archive) as bundle:
        members=bundle.getmembers()
        assert len(members)==len(expected) and {m.name for m in members}==set(expected)
        for member in members:
            data=bundle.extractfile(member).read()
            spec=expected[member.name]
            assert hashlib.sha256(data).hexdigest()==spec['sha256']
            assert len(data)==spec['bytes'] and member.mode==int(spec['mode'],8)
    inputs=dict(archive_sha256=sha(archive),archive_bytes=archive.stat().st_size,
        export_manifest_sha256=sha(ROOT/'offline-export-manifest.json'),
        control_plan_sha256=sha(ROOT/'offline-control-plan.json'),
        reconstruction_receipt_sha256=sha(ROOT/'macs-742-image-readback-001.json'),
        verified_archive_members=len(expected),controls_executed=False,model_calls=0)
    (ROOT/'offline-control-inputs.json').write_text(json.dumps(inputs,indent=2)+'\n')
    print(json.dumps(inputs))

if __name__=='__main__':main()
