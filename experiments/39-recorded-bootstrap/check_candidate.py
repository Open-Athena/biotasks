"""Native static validation and explicit allowed metadata differences only."""
from dataclasses import asdict
import json
from pathlib import Path
import sys
import tomllib

from common import UPSTREAM,inventory,sha,write
from prepare_candidate import grading_contract

ROOT=Path(__file__).resolve().parent


def differences(before,after,path=''):
    if isinstance(before,dict) and isinstance(after,dict):
        return [row for key in sorted(before.keys()|after.keys()) for row in differences(before.get(key),after.get(key),path+'.'+key)]
    return [] if before==after else [dict(path=path.lstrip('.'),before=before,after=after)]


def main():
    prep=json.loads((ROOT/'candidate-preparation.json').read_text());candidate=ROOT/'inputs-private/candidate/tree/outputs/OHIF__Viewers'/prep['task']
    original=ROOT/'inputs-private/candidate/original/OHIF__Viewers'/prep['task']
    assert inventory(candidate)==prep['candidate_files'] and inventory(original)==prep['original_files']
    before=(original/'task.toml').read_bytes();after=(candidate/'task.toml').read_bytes()
    assert grading_contract(before)==grading_contract(after)
    delta=differences(tomllib.loads(before.decode()),tomllib.loads(after.decode()))
    assert all(r['path'].startswith('metadata.repo2env.reproducibility.') or r['path'] in
        ['metadata.repo2env.spec_version','metadata.repo2env.pr_runtime.bootstrap_image'] for r in delta)
    package=ROOT.parents[2]/'31/experiments/31-historical-builds/inputs-private/upstream-package'
    acquisition=json.loads((package.parents[1]/'package-acquisition.json').read_text());assert acquisition['revision']==UPSTREAM
    for row in acquisition['files']:assert sha(package/row['path'])==row['sha256']
    def audit(event,args):
        if event in ('socket.connect','socket.getaddrinfo','subprocess.Popen','os.system'):raise AssertionError(event)
        if event=='open' and isinstance(args[0],str):
            p=str(Path(args[0]).resolve());assert not any(s in p for s in ['.codex/secrets/','.config/gh/','.config/coreweave/','.cache/huggingface/token','.git-credentials','.docker/config.json'])
    sys.addaudithook(audit);sys.path[:0]=[str(package/'src'),str(package.parent/'check-deps')]
    from repo2rlenv.validation import validate_task
    findings=[asdict(f) for f in validate_task(candidate,tomllib.loads(after.decode()),oracle=True)]
    result=dict(issue=39,scope='Native static diagnostics and exact declared metadata diff; no runtime validation',
        candidate_task_identity=prep['candidate_task_identity'],findings=findings,
        errors=sum(f['severity']=='error' for f in findings),warnings=sum(f['severity']=='warning' for f in findings),
        grading_contract_unchanged=True,allowed_metadata_differences=delta,original_overlay_commands_unchanged=prep['original_overlay_commands_unchanged'],
        mode=tomllib.loads(after.decode())['metadata']['repo2env']['reproducibility']['mode'],initialization_required=True,docker_calls=0,model_calls=0)
    write(ROOT/'candidate-static-findings.json',result)
    assert result['errors']==0
    print(json.dumps(dict(errors=result['errors'],warnings=result['warnings'],allowed_metadata_differences=len(delta),docker_calls=0,model_calls=0)))


if __name__=='__main__':main()
