"""Freeze the explicit dependency variant using original task/native ref writers."""
from copy import deepcopy
import json
from pathlib import Path
import sys
import tarfile
import tomllib

from common import UPSTREAM,archive_tree,content_sha,inventory,json_sha,safe,sha,task_identity,write
from evidence import archive_records

ROOT=Path(__file__).resolve().parent
TREE=ROOT.parents[2]


def grading_contract(raw):
    value=deepcopy(tomllib.loads(raw.decode()))
    r2e=value.get('metadata',{}).get('repo2env',{})
    r2e.pop('reproducibility',None);r2e.pop('spec_version',None)
    pipeline=r2e.get('pipeline')
    if isinstance(r2e.get(pipeline),dict):r2e[pipeline].pop('bootstrap_image',None)
    return value


def main():
    plan=json.loads((ROOT/'source-plan.json').read_text());assessment=json.loads((ROOT/'source-assessment.json').read_text())
    assert sha(ROOT/'source-assessment.json')==plan['source_assessment_sha256']
    assert sha(ROOT/'interface-assessment.json')==plan['interface_assessment_sha256']
    for row in assessment['inputs']:assert sha(ROOT/row['path'])==row['sha256']
    original_manifest=json.loads((TREE/'33/experiments/33-unattended-validation/task-execution-ledger.json').read_text())
    original=next(t for t in original_manifest['tasks'] if t['task']==plan['task'])
    assert original['task_content_identity_sha256']==plan['original_task_identity']
    relative='outputs/'+plan['repo'].replace('/','__')+'/'+plan['task']+'/'
    baseline=archive_records(ROOT/'inputs-private/native-baseline-task.tar.gz','tar.gz')
    baseline_rows=[dict(path=n.removeprefix(relative),bytes=r['bytes'],mode=format(r['mode'],'o'),sha256=r['sha256']) for n,r in baseline.items()]
    assert task_identity(plan['repo'],plan['task'],baseline_rows)==plan['native_prepared_identity']
    phase=TREE/'29/experiments/29-runtime-limits/inputs-private/OHIF__Viewers-phase.tar.gz'
    assert sha(phase)==assessment['source_phase_sha256']
    expected={relative+f['path']:f for f in original['original_task_files']}
    selected={};total=0
    with tarfile.open(phase,'r|gz') as tar:
        for member in tar:
            safe(member.name);total+=member.size;assert total<256*1024**2
            if member.name not in expected:continue
            assert member.isfile() and member.name not in selected
            spec=expected[member.name];raw=tar.extractfile(member).read()
            assert len(raw)==spec['bytes']<1024**2 and member.mode==spec['mode'] and content_sha(raw)==spec['sha256']
            selected[member.name]=dict(data=raw,mode=member.mode)
    assert set(selected)==set(expected)
    destination=ROOT/'inputs-private/candidate';assert not destination.exists();destination.mkdir(mode=0o700)
    original_root=destination/'original'/relative.removeprefix('outputs/')
    candidate_root=destination/'tree'/relative
    for name,row in selected.items():
        rel=name.removeprefix(relative)
        for base in [original_root,candidate_root]:
            p=base/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(row['data']);p.chmod(row['mode'])
        if rel not in ('environment/Dockerfile','task.toml'):
            assert baseline[name]['data']==row['data'] and baseline[name]['mode']==row['mode']
    assert task_identity(plan['repo'],plan['task'],inventory(original_root))==plan['original_task_identity']
    original_df=(original_root/'environment/Dockerfile').read_bytes()
    lines=original_df.splitlines(keepends=True);positions=[i for i,line in enumerate(lines) if line.startswith(b'FROM ')]
    assert len(positions)==1;position=positions[0];overlay=b''.join(lines[position+1:])
    assert baseline[relative+'environment/Dockerfile']['data'].endswith(overlay)
    assert grading_contract(selected[relative+'task.toml']['data'])==grading_contract(baseline[relative+'task.toml']['data'])
    package=TREE/'31/experiments/31-historical-builds/inputs-private/upstream-package'
    source_manifest=json.loads((package.parents[1]/'package-acquisition.json').read_text());assert source_manifest['revision']==UPSTREAM
    for row in source_manifest['files']:assert sha(package/row['path'])==row['sha256']
    source_files={name:sha(package/'src/repo2rlenv'/name) for name in ['auth.py','bootstrap/docker.py','bootstrap/runner.py','registry/integration.py']}
    definition=dict(repo=plan['repo'],bootstrap_ref=plan['bootstrap_ref'],public_base_ref=plan['public_base_ref'],
        expected_base_image_id=plan['expected_base_image_id'],actions_sha256=sha(ROOT/'inputs-private/recorded-actions.json'),
        replay_helper_sha256=sha(ROOT/'recorded_replay.py'),native_source_sha256=source_files)
    dependency_ref='local/r2e-replay/'+plan['repo'].lower().replace('/','__')+':'+json_sha(definition)[:20]
    blocked=[]
    def audit(event,args):
        if event in ('socket.connect','socket.getaddrinfo','subprocess.Popen','os.system'):
            blocked.append(event);raise AssertionError(event)
        if event=='open' and isinstance(args[0],str):
            p=str(Path(args[0]).resolve())
            if any(s in p for s in ['.codex/secrets/','.config/gh/','.config/coreweave/','.cache/huggingface/token','.git-credentials','.docker/config.json']):
                blocked.append('credential_store_open');raise AssertionError('Credential store access')
    sys.addaudithook(audit)
    sys.path[:0]=[str(package/'src'),str(package.parent/'check-deps')]
    from repo2rlenv.registry import integration as native
    assert Path(native.__file__).resolve()==package/'src/repo2rlenv/registry/integration.py'
    assert native._rewrite_dockerfile_from(candidate_root/'environment/Dockerfile',dependency_ref)
    native._update_task_toml_reproducibility(candidate_root/'task.toml',mode='local_only',image_ref=dependency_ref,
        image_tag=dependency_ref,image_visibility='private',pushed_by=None,
        fallback_reason='Explicit recorded-bootstrap dependency; run the packaged initializer before task build. No public image or standalone Dockerfile claim.')
    candidate_df=(candidate_root/'environment/Dockerfile').read_bytes();new_lines=candidate_df.splitlines(keepends=True)
    assert new_lines[:position]==lines[:position] and new_lines[position+1:]==lines[position+1:]
    assert new_lines[position]==('FROM '+dependency_ref+'\n').encode()
    candidate_toml=(candidate_root/'task.toml').read_bytes()
    assert grading_contract(candidate_toml)==grading_contract(selected[relative+'task.toml']['data'])
    toml=tomllib.loads(candidate_toml.decode());assert toml['verifier']['timeout_sec']==300
    assert toml['metadata']['repo2env']['reproducibility']['mode']=='local_only'
    before={r['path']:r for r in inventory(original_root)};after={r['path']:r for r in inventory(candidate_root)}
    changes=[p for p in sorted(before) if before[p]!=after[p]]
    assert changes==['environment/Dockerfile','task.toml']
    assert not blocked
    bundle=archive_tree(destination/'tree',destination/'tasks.tar.gz');bundle['path']=str(Path(bundle['path']).relative_to(ROOT))
    descriptor=dict(schema_version=1,kind='recorded_bootstrap_dependency',**definition,dependency_ref=dependency_ref,
        original_bootstrap_json_sha256=sha(ROOT/'inputs-private/original-bootstrap.json'),recorded_action_timeout_seconds=300,
        initialization_required=True,image_pushed=False,task_dockerfile_alone_standalone=False,
        clone_and_shell='Original pinned clone/ref helpers, DockerSandbox complete checkout copy and bash -lc execution',
        order='Replay exact original actions, original smoke/git checks, commit, remove source sandbox, original fresh-image check, then task build/controls')
    write(ROOT/'bootstrap-dependency.json',descriptor)
    result=dict(issue=39,repo=plan['repo'],task=plan['task'],upstream_revision=UPSTREAM,source_plan_sha256=sha(ROOT/'source-plan.json'),
        source_assessment_sha256=sha(ROOT/'source-assessment.json'),interface_assessment_sha256=sha(ROOT/'interface-assessment.json'),
        original_task_identity=plan['original_task_identity'],native_baseline_identity=plan['native_prepared_identity'],
        candidate_task_identity=task_identity(plan['repo'],plan['task'],inventory(candidate_root)),
        base_commit=original['base_commit'],head_commit=original['head_commit'],expected_f2p=plan['expected_f2p'],expected_p2p=plan['expected_p2p'],
        grading_assets_unchanged=8,original_overlay_commands_unchanged=True,parsed_grading_contract_unchanged=True,
        changed_files=changes,original_files=inventory(original_root),candidate_files=inventory(candidate_root),
        task_bundle=bundle,bootstrap_dependency_sha256=sha(ROOT/'bootstrap-dependency.json'),dependency_ref=dependency_ref,
        image_visibility='private',initialization_required=True,task_dockerfile_alone_standalone=False,
        native_helpers_executed=['_rewrite_dockerfile_from','_update_task_toml_reproducibility'],native_source_sha256=source_files,
        audit_guard=dict(blocked_events=blocked,network_subprocess_credential_access=False),
        original_phase_verified=True,original_package_identity_verified=True,model_calls=0,docker_calls=0,remote_admission=False)
    write(ROOT/'candidate-preparation.json',result)
    print(json.dumps(dict(candidate_task_identity=result['candidate_task_identity'],changed_files=changes,grading_assets_unchanged=8,
        original_overlay_commands_unchanged=True,dependency_ref=dependency_ref,initialization_required=True,docker_calls=0,model_calls=0)))


if __name__=='__main__':main()
