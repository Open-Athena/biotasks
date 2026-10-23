"""Freeze existing OHIF exports and identity-only controls supervisor adaptation."""
import hashlib
import importlib.util
import json
from pathlib import Path
import tarfile

ROOT = Path(__file__).resolve().parent

def sha(data):
    return hashlib.sha256(data).hexdigest()

def main():
    spec = importlib.util.spec_from_file_location('controls', ROOT/'run_existing_controls.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    repo = next(r for r in json.loads((ROOT/'control-plan.json').read_text())['repositories'] if r['repo']=='OHIF/Viewers')
    source = ROOT/'inputs-private/controls'
    hashes = module.inspect_tasks(repo, source)
    rows = module.commands(repo, Path('/work'), Path('/work/harbor066/bin/harbor'), Path('/work/jobs/ohif-controls'))
    assert len(hashes)==40 and len(rows)==8
    assert all(r['verifier_timeout_seconds']==300 for r in rows)
    archive = ROOT/'inputs-private/ohif-control-tasks.tar.gz'
    assert not archive.exists(), 'Do not overwrite frozen inputs'
    with tarfile.open(archive, 'w:gz') as out:
        for name in sorted(hashes):
            out.add(source/name, arcname=name, recursive=False)
    result_bytes = (ROOT/'ohif-recorded-result-001.json').read_bytes()
    result = json.loads(result_bytes)
    image = {'image_id':result['image_id'], 'retained_image':result['retained_image_tag'], 'source_result_sha256':sha(result_bytes), 'reconstruction_kind':'original recorded BASH actions; no task repair', 'smoke_passed':result['smoke_passed'], 'verify_passed':result['verify_passed']}
    (ROOT/'ohif-controls-image.json').write_text(json.dumps(image,indent=2)+'\n')
    receipt = {'files_verified':len(hashes), 'task_file_hashes':hashes, 'archive_sha256':sha(archive.read_bytes()), 'archive_bytes':archive.stat().st_size, 'commands':rows, 'original_files_edited':False, 'controls_run':0}
    (ROOT/'ohif-controls-inputs.json').write_text(json.dumps(receipt,indent=2)+'\n')

if __name__=='__main__':
    main()
