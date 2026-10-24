"""Acquire only hash-bound original bootstrap metadata from its public phase archive."""
import hashlib
import json
import os
from pathlib import Path
import tarfile
import tempfile

ROOT=Path(__file__).resolve().parent


def sha(path):
    with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def main():
    epic=ROOT.parents[2]/'33/experiments/33-unattended-validation'
    source=ROOT.parents[2]/'36/experiments/36-inline-cache-identity'
    frozen=json.loads((source/'original-inputs.json').read_text())
    original_manifest=ROOT.parents[3]/'experiments/28-catalogued-fields/history-wide/archives/OHIF__Viewers-manifest.json'
    assert sha(original_manifest)==frozen['original_manifest_sha256']
    manifest=json.loads(original_manifest.read_text())
    phase=next(r for r in manifest['files'] if r['path']=='evidence/phase-artifacts.tar.gz')
    assert phase['sha256']==frozen['phase_sha256'] and phase['bytes']<16*1024**2
    member_name=frozen['cache']['path'].removeprefix('workspace/')
    member_spec=next(r for r in phase['members'] if r['path']==member_name)
    assert member_spec['sha256']==frozen['cache']['sha256']
    os.environ.update(json.loads((epic/'archive-client-profile.json').read_text())['environment'])
    with tempfile.TemporaryDirectory(prefix='bootstrap-readback-',dir=ROOT/'inputs-private') as td:
        os.environ['HF_XET_CACHE']=str(Path(td)/'xet')
        from huggingface_hub import HfApi
        from huggingface_hub.utils import disable_progress_bars
        disable_progress_bars()
        archive=Path(td)/'phase.tar.gz'
        remote='research/28-catalogued-fields/2026-10-23/'+sha(original_manifest)+'/'+phase['path']
        HfApi(token=False).download_bucket_files('open-athena/biotasks',[(remote,archive)],raise_on_missing_files=True,token=False)
        assert archive.stat().st_size==phase['bytes'] and sha(archive)==phase['sha256']
        data=None;total=0
        with tarfile.open(archive,'r|gz') as tar:
            for member in tar:
                total+=member.size;assert total<256*1024**2
                if member.name!=member_name:continue
                assert member.isfile() and member.size==member_spec['bytes']<1024**2
                data=tar.extractfile(member).read();break
        assert data is not None and hashlib.sha256(data).hexdigest()==member_spec['sha256']
    cache=json.loads(data)
    destination=ROOT/'inputs-private/original-bootstrap.json'
    assert not destination.exists();destination.write_bytes(data)
    report=dict(repo=cache['repo'],ref=cache['ref'],image_tag=cache['image_tag'],
        bootstrap_json_sha256=hashlib.sha256(data).hexdigest(),
        phase_archive_sha256=phase['sha256'],phase_archive_bytes=phase['bytes'],public_source_path=remote,
        commands={key:cache.get(key) for key in ['setup_cmds','rebuild_cmds','test_cmds']},
        original_fields_available=sorted(cache),
        anonymous_source_readback_verified=True,download_and_cache_removed=True,
        model_calls=0,docker_commands=0,scope='Original recorded command provenance only; no command replay')
    (ROOT/'bootstrap-provenance.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ('original_fields_available','public_source_path')}))


if __name__=='__main__':main()
