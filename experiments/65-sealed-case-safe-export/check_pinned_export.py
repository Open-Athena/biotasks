"""Original pinned API on our own metadata fixtures; no Docker/model/repo code."""
import json
import sys
import tomllib
from pathlib import Path
from biotasks.generation import handoff
from biotasks.validation.files import inventory,json_sha,read_json,sha,write_json,ValidationError

BASE=Path(__file__).resolve().parent
MODE=sys.argv[1]
ROOT=BASE/'inputs-private/pinned-api-001'
REFERENCE=BASE.parents[2]/'62/experiments/62-fresh-dendropy/inputs-private/run-001/dendropy-handoff/handoff-config.json'


def main():
    original=read_json(REFERENCE)
    native=handoff.source_api(Path(original['upstream_source']),Path(original['upstream_manifest']),Path(original['upstream_extra_modules']))
    rows=[]
    for label,owner,repo in [('lower','owner','mixed'),('mixed','OwNeR','MiXeD')]:
        folder=ROOT/label; raw=folder/'raw';cache=folder/'cache';task=raw/'own-fixture'
        tag='local/r2e-bootstrap/owner__mixed:'+'a'*12
        if MODE=='original':
            for name in ['environment','solution','tests']:(task/name).mkdir(parents=True)
            (task/'task.toml').write_text('[metadata.repo2env]\npipeline="pr_runtime"\nrepo="'+owner+'/'+repo+'"\n[metadata.repo2env.pr_runtime]\nbase_commit="'+'a'*40+'"\n[verifier]\ntimeout_sec=300\n[agent]\ntimeout_sec=1800\n')
            (task/'environment/Dockerfile').write_text('FROM '+tag+'\nWORKDIR /workspace\nRUN true\n')
            (task/'environment/docker-compose.yaml').write_text('services:\n  main:\n    extra_hosts:\n      - "github.com:0.0.0.0"\n')
            for name in ['instruction.md','solution/patch.diff','solution/solve.sh','tests/test.sh','tests/verifier.py']:(task/name).write_text('Our own synthetic fixture; never executed.\n')
            for name in ['f2p','p2p']:write_json(task/'tests'/f'{name}.json',['test_'+name])
            slot=cache/(owner+'__'+repo)/('a'*12+'__options');slot.mkdir(parents=True)
            write_json(slot/'bootstrap.json',dict(repo=owner+'/'+repo,ref='a'*40,image_tag=tag,rebuild_cmds=['python -m pip install -e .'],test_cmds=['python -m pytest -v'],language='python',dockerfile_reconstruction='FROM python:3.12-slim\n'))
        before_raw,before_cache=inventory(raw),inventory(cache)
        config={**original,'raw_exports':str(raw),'bootstrap_cache':str(cache),
                'raw_inventory_sha256':json_sha(before_raw),'cache_inventory_sha256':json_sha(before_cache),
                'output_directory':str(folder/(MODE+'-output'))}
        try:
            result=handoff.prepare(config,native)
        except ValidationError as error:
            assert MODE=='original' and label=='mixed',str(error)
            rows.append(dict(case=label,state='rejected',error=str(error)))
        else:
            prepared=folder/(MODE+'-output/handoff/prepared')
            assert result['task_count']==1 and result['model_calls']==result['remote_jobs']==0
            assert handoff.grading_contract(task/'task.toml')==handoff.grading_contract(prepared/'own-fixture/task.toml')
            for f in ['instruction.md','solution/patch.diff','solution/solve.sh','tests/test.sh','tests/verifier.py','tests/f2p.json','tests/p2p.json','environment/docker-compose.yaml']:
                assert (task/f).read_bytes()==(prepared/'own-fixture'/f).read_bytes()
            snapshot=inventory(folder/(MODE+'-output'))
            assert handoff.prepare(config,native)==result and inventory(folder/(MODE+'-output'))==snapshot
            if MODE=='candidate' and label=='lower':
                older=folder/'original-output/handoff/prepared'
                before_files, after_files = inventory(older), inventory(prepared)
                assert [x["path"] for x in before_files] == [x["path"] for x in after_files]
                for f in before_files:
                    if not f["path"].endswith("task.toml"):
                        assert (older/f["path"]).read_bytes() == (prepared/f["path"]).read_bytes()
                a=tomllib.loads((older/'own-fixture/task.toml').read_text())
                b=tomllib.loads((prepared/'own-fixture/task.toml').read_text())
                a['metadata']['repo2env']['reproducibility'].pop('pushed_at')
                b['metadata']['repo2env']['reproducibility'].pop('pushed_at')
                assert a==b
            rows.append(dict(case=label,state='prepared',result=result,prepared_grading_assets_preserved=True,completed_replay_byte_inert=True))
        assert inventory(raw)==before_raw and inventory(cache)==before_cache
    write_json(BASE/(MODE+'-pinned-api-proof.json'),dict(mode=MODE,cases=rows,actual_pinned_api=True,upstream_source_modified=False,synthetic=True,native_or_model_calls=0,original_inputs_unchanged=True))
    print(json.dumps({'mode':MODE,'cases':[(x['case'],x['state']) for x in rows],'native_or_model_calls':0}))

if __name__=='__main__':main()
