"""Compare native versus an explicit lookup-only candidate on unchanged OHIF copies."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import tomllib
from copy import deepcopy
from dataclasses import asdict

from resolver_candidate import resolve

ROOT=Path(__file__).resolve().parent
PRIOR=ROOT.parents[2]/'31/experiments/31-historical-builds'


def inventory(root):
    return {str(p.relative_to(root)):dict(bytes=p.stat().st_size,mode=p.stat().st_mode&0o777,
        sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in sorted(root.rglob('*')) if p.is_file()}


def contract(data):
    data=deepcopy(data);metadata=data.get('metadata',{}).get('repo2env',{})
    metadata.pop('reproducibility',None);metadata.pop('spec_version',None)
    return data


def main():
    inputs=json.loads((ROOT/'original-inputs.json').read_text())
    source=ROOT/'inputs-private/ohif-source'
    original=inventory(source/'original')
    assert original==inputs['original_inventory']
    assert hashlib.sha256((source/inputs['cache']['path']).read_bytes()).hexdigest()==inputs['cache']['sha256']
    fixtures=json.loads((ROOT/'fixture-results.json').read_text())
    assert fixtures['fixture_cases_passed']==10 and fixtures['relevant_upstream_functions_identical']
    package=PRIOR/'inputs-private/upstream-package'
    acquisition=json.loads((PRIOR/'package-acquisition.json').read_text())
    for row in acquisition['files']:
        assert hashlib.sha256((package/row['path']).read_bytes()).hexdigest()==row['sha256']
    blocked=[]
    def audit(event,args):
        if event in ('socket.connect','socket.getaddrinfo','subprocess.Popen','os.system'):
            blocked.append(event);raise AssertionError(event)
        if event=='open' and isinstance(args[0],str):
            path=str(Path(args[0]).resolve())
            if any(name in path for name in ('.codex/secrets/','.config/gh/','.config/coreweave/','.cache/huggingface/token','.git-credentials','.docker/config.json')):
                blocked.append('credential_store_open');raise AssertionError('Credential store access')
    sys.addaudithook(audit)
    sys.path[:0]=[str(package/'src'),str(PRIOR/'inputs-private/check-deps')]
    from repo2rlenv.registry import integration as native
    assert Path(native.__file__).resolve()==package/'src/repo2rlenv/registry/integration.py'
    original_reader=native._load_bootstrap_recipe;rows=[];cwd=Path.cwd()
    try:
        for name in ['baseline','candidate']:
            work=ROOT/'inputs-private'/name
            assert not work.exists(), 'Preserve previous comparison; never overwrite'
            shutil.copytree(source/'original',work/'tasks')
            shutil.copytree(source/'workspace',work/'workspace')
            os.chdir(work)
            if name=='candidate':
                native._load_bootstrap_recipe=lambda ref:resolve(ref,native._parse_local_tag,native._build_clean_recipe)
            else:native._load_bootstrap_recipe=original_reader
            try:
                outcome=native.prepare_dataset_for_push(work/'tasks',hf_owner='open-athena',
                    inline_dockerfile=True,pushed_by='biotasks-issue36')
                result=dict(variant=name,state='prepared',native_result=asdict(outcome))
            except RuntimeError as error:
                result=dict(variant=name,state='unsupported',error=str(error))
            after=inventory(work/'tasks');assert set(after)==set(original)
            changed=[n for n in original if original[n]!=after[n]]
            if name=='baseline':assert result['state']=='unsupported' and changed==[]
            else:
                assert result['state']=='prepared' and result['native_result']['tasks_rewritten']==12
                expected=sorted(task+'/'+file for task in inputs['tasks'] for file in ['environment/Dockerfile','task.toml'])
                assert changed==expected
                for task in inputs['tasks']:
                    before_config=tomllib.loads((source/'original'/task/'task.toml').read_text())
                    after_config=tomllib.loads((work/'tasks'/task/'task.toml').read_text())
                    assert contract(before_config)==contract(after_config)
            result.update(changed_files=changed,inventory=after,
                unchanged_grading_assets=96 if name=='candidate' else 120,
                grading_contract_unchanged=True)
            rows.append(result)
    finally:
        native._load_bootstrap_recipe=original_reader;os.chdir(cwd)
    assert inventory(source/'original')==original
    report=dict(repo='OHIF/Viewers',original_tasks=12,variants=rows,
        baseline_revision=acquisition['revision'],native_source_files_modified=False,
        candidate_in_memory_override=['_load_bootstrap_recipe'],
        candidate_sha256=hashlib.sha256((ROOT/'resolver_candidate.py').read_bytes()).hexdigest(),
        blocked_operations=blocked,model_calls=0,docker_commands=0,uploads=0,
        scope='Metadata preparation comparison only; no image build, control execution or portability claim')
    (ROOT/'metadata-comparison.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(original_tasks=12,baseline='unsupported',candidate_prepared=12,
        unchanged_grading_assets=96,grading_contract_unchanged=True,model_calls=0,docker_commands=0)))


if __name__=='__main__':main()
