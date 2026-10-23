"""Exercise transformation on exact archived task, without Docker or execution."""
import argparse
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from prepare_control_variant import prepare
from run_existing_controls import inspect_tasks, commands

p=argparse.ArgumentParser()
p.add_argument('--original',type=Path,required=True)
p.add_argument('--original-plan',type=Path,required=True)
a=p.parse_args()
checks=[]
with TemporaryDirectory(prefix='biotasks34-variant-') as tmp:
    output=Path(tmp)/'outputs/macs3-project__MACS/macs3-project__MACS-742'
    output.parent.mkdir(parents=True)
    plan,manifest=prepare(a.original,a.original_plan,'sha256:'+'0'*64,output)
    assert len(manifest['task_files'])==12
    assert manifest['unchanged_original_files']==9
    for rel in ['environment/docker-compose.yaml','tests/test.sh','tests/verifier.py','solution/patch.diff','instruction.md','task.toml']:
        assert (output/rel).read_bytes()==(a.original/rel).read_bytes()
    checks.append('original task assets and egress guard preserved')
    checks.append('only Dockerfile changed plus two preparation helpers')
    try:prepare(a.original,a.original_plan,'sha256:'+'0'*64,output)
    except AssertionError:checks.append('existing variant overwrite rejected')
    else:raise AssertionError('overwrote variant')
    try:prepare(a.original,a.original_plan,'mutable:tag',Path(tmp)/'invalid')
    except AssertionError:checks.append('mutable image tag rejected')
    else:raise AssertionError('accepted mutable tag')
    dockerfile=(output/'environment/Dockerfile').read_text()
    assert 'PIP_NO_INDEX=1' in dockerfile and '--no-build-isolation' not in dockerfile
    checks.append('offline pip configuration preserves build isolation')
    hashes=inspect_tasks(plan['repositories'][0],Path(tmp))
    rows=commands(plan['repositories'][0],Path(tmp),Path('/unused/harbor'),Path(tmp)/'jobs')
    assert len(hashes)==12 and len(rows)==2
    assert [r['agent'] for r in rows]==['nop','oracle']
    assert all(r['verifier_timeout_seconds']==300 for r in rows)
    checks.append('unchanged control runner accepts all candidate hashes and emits two 300s controls')
result=dict(checks=checks,original_plan_sha256=hashlib.sha256(a.original_plan.read_bytes()).hexdigest(),
    fixture_image_digest_only=True,task_executed=False,temporary_variant_removed=not output.exists())
Path(__file__).with_name('control-variant-checks.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result))
