"""Render only commands selected by the general candidate; bind both stages."""
import copy
import hashlib
import json
from pathlib import Path
from check_deleted_targets import load

ROOT = Path(__file__).resolve().parent
CANDIDATE_SHA = '2c0518b3ae303055e834e080747ecb9b856c47adc6f66de8493b2ddb369f2300'


def render(validator):
    source=ROOT/'candidate/pr_runtime_targeting.py'
    assert hashlib.sha256(source.read_bytes()).hexdigest()==CANDIDATE_SHA
    candidate=load(source)
    manifest=json.loads((ROOT/'live-script-manifest.json').read_text())
    result=copy.deepcopy(manifest)
    result['scope']='Frozen same-input selection comparison, candidate excludes deleted diff destinations only'
    result['selection_candidate_sha256']=CANDIDATE_SHA
    scripts={}
    for case in result['cases']:
        diff=(ROOT/'inputs-private'/f"{case['pr']}-test.patch").read_text()
        assert hashlib.sha256(diff.encode()).hexdigest()==case['test_patch_sha256']
        case['test_files']=candidate['_runnable_test_files_in_patch'](diff)
        recorded=candidate['normalize_test_cmds_for_runtime'](['cd /workspace && python -m pytest -v'])
        case['commands']=candidate['targeted_test_cmds_for_pr'](recorded,case['test_files'])
        patch=(ROOT/'inputs-private'/f"{case['pr']}-source.patch").read_text()
        assert hashlib.sha256(patch.encode()).hexdigest()==case['source_patch_sha256']
        for side in ('pre','post'):
            script=validator._build_stage_script(case['base_sha'],apply_patch=patch if side=='post' else None,
                apply_test_patch=diff,test_cmds=case['commands'])
            data=script.encode()
            scripts[f"{case['pr']}-{side}-targets.sh"]=data
            case['stages'][side]={'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}
    return result,scripts


def verify_target_inputs(validator):
    expected,scripts=render(validator)
    assert expected==json.loads((ROOT/'targeted-script-manifest.json').read_text())
    for name,data in scripts.items():assert (ROOT/'inputs-private'/name).read_bytes()==data
    return expected


def main():
    from live_validation import load_sources,verify_inputs
    _,_,_,validator=load_sources()
    verify_inputs(validator)
    manifest,scripts=render(validator)
    for name,data in scripts.items():
        p=ROOT/'inputs-private'/name;p.write_bytes(data);p.chmod(0o600)
    (ROOT/'targeted-script-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps({'cases':[{'pr':r['pr'],'targets':len(r['test_files'])} for r in manifest['cases']]}))


if __name__=='__main__':main()
