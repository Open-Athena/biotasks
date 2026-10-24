"""Publish and cold-read the exact portable initializer before admission."""
from datetime import datetime,timezone
import json
from pathlib import Path
import shutil
import subprocess

from common import safe,sha,write,unpack_task_archive
from preserve import BUCKET,inspect,publish

ROOT=Path(__file__).resolve().parent
DIRECTORY=ROOT/'private/input-publication'


def verify(directory):
    directory=Path(directory);manifest=json.loads((directory/'manifest.json').read_text())
    assert manifest['issue']==39 and manifest['kind']=='portable_initializer_inputs' and manifest['bucket']==BUCKET
    assert manifest['policy_sha256']==sha(ROOT/'public-policy.json')
    expected={'inputs.tar.gz','cohort.json','public-policy.json','candidate-preparation.json','candidate-static-findings.json','source-assessment.json','interface-assessment.json'}
    assert {r['path'] for r in manifest['files']}==expected
    for row in manifest['files']:
        path=directory/'snapshot'/safe(row['path'])
        assert sha(path)==row['sha256'] and path.stat().st_size==row['bytes']
        assert inspect(path.read_bytes(),row.get('archive_format'))==row.get('members')
    return manifest


def main():
    cohort=json.loads((ROOT/'cohort.json').read_text());policy=json.loads((ROOT/'public-policy.json').read_text())
    assert policy['public_eligible'] and policy['cohort_sha256']==sha(ROOT/'cohort.json')
    DIRECTORY.mkdir(mode=0o700,parents=True,exist_ok=True)
    if not (DIRECTORY/'manifest.json').exists():
        assert not (DIRECTORY/'publication-intent.json').exists()
        snapshot=DIRECTORY/'snapshot';assert not snapshot.exists();snapshot.mkdir()
        files=[]
        for name in ['inputs.tar.gz','cohort.json','public-policy.json','candidate-preparation.json','candidate-static-findings.json','source-assessment.json','interface-assessment.json']:
            source=ROOT/cohort['portable_input_bundle']['path'] if name=='inputs.tar.gz' else ROOT/name
            destination=snapshot/name;shutil.copyfile(source,destination)
            kind='tar.gz' if name.endswith('.tar.gz') else None
            members=inspect(destination.read_bytes(),kind)
            row=dict(path=name,bytes=destination.stat().st_size,sha256=sha(destination))
            if kind:row.update(archive_format=kind,members=members)
            files.append(row)
        write(DIRECTORY/'manifest.json',dict(schema_version=1,issue=39,kind='portable_initializer_inputs',bucket=BUCKET,visibility='public',
            created_utc=datetime.now(timezone.utc).isoformat(),policy_sha256=sha(ROOT/'public-policy.json'),files=files,
            source_research_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
            retention='Retain while cited; no automatic deletion.',initializer_required=True,task_dockerfile_alone_standalone=False))
    receipt=publish(DIRECTORY,verifier=verify)
    # A second anonymous transfer becomes the sole source for compiled runtime inputs.
    from huggingface_hub import HfApi
    cold=ROOT/'inputs-private/cold';cold.mkdir(mode=0o700,exist_ok=True)
    archive=cold/'inputs.tar.gz';bundle=cohort['portable_input_bundle']
    HfApi().download_bucket_files(BUCKET,[(receipt['prefix']+'/inputs.tar.gz',archive)],raise_on_missing_files=True,token=False)
    assert sha(archive)==bundle['sha256'] and archive.stat().st_size==bundle['bytes']
    target=cold/'tree'
    if not target.exists():unpack_task_archive(archive,bundle['files'],target)
    else:
        from common import inventory
        assert inventory(target)==bundle['files']
    write(ROOT/'input-evidence-manifest.json',verify(DIRECTORY));write(ROOT/'input-evidence-receipt.json',receipt)
    write(ROOT/'cold-input-readback.json',dict(bucket=BUCKET,prefix=receipt['prefix'],anonymous_download_verified=True,
        archive_sha256=sha(archive),members_verified=len(bundle['files']),runtime_input_root=str(target.relative_to(ROOT)),model_calls=0))
    print(json.dumps(dict(public_objects=len(receipt['objects']),portable_members=len(bundle['files']),prefix=receipt['prefix'],cold_inputs_verified=True)))


if __name__=='__main__':main()
