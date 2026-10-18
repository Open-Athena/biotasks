"""Validate the frozen broader PR profile/cache without services or allocation."""
import copy
import hashlib
import json
import tempfile
from pathlib import Path
from repo2rlenv.spec.input import GenerationInput
from run_history_recipe import prepare

root=Path(__file__).resolve().parent
profile=json.loads((root/'swe-next-biopython-broader-profile.json').read_text())
settings=json.loads((root/'glm-generation-adaptation.json').read_text())
source=root/'evidence/biopython-broader-pr-preparation/pulls.json'
raw=source.read_bytes();digest=hashlib.sha256(raw).hexdigest()
review=json.loads((source.parent/'source-review.json').read_text());assert digest==review['pulls_sha256']
assert profile['prior_considered_candidates']+profile['selected_additional_sources']<=10
assert profile['options']['install_command']==json.loads((root/'r2e-gym-biopython-seqfeature-profile.json').read_text())['options']['install_command']
with tempfile.TemporaryDirectory() as temporary:
    base=Path(temporary)
    spec=GenerationInput.model_validate({'repo':profile['repo'],'pipeline':{'name':'pr_runtime','recipe':'swe_next'},
        'llm':{'provider':'openai','model':'glm-5.3','endpoint':'https://unused.example/v1','api_key_env':'UNUSED_FIXTURE_KEY','max_concurrent':1,'timeout_sec':1200,'fallback':None},
        'execution':{'worker_receipt':str(base/'pending-worker.json'),'runtime_wheel':str(base/'unused.whl'),'campaign_dir':str(base/'campaign'),'run_id':profile['run_id'],'timeout_sec':6600,'resume':False},
        'output':{'destination':str(base/'tasks'),'org':'open-athena','dataset_name':'biotasks21-history'},'auth':{'use_gh_cli':False}})
    pipeline,options=prepare(spec,profile,settings,source,digest)
    assert options.pr_numbers==[5308,5316,5310] and options.target==3 and options.max_candidates==10
    assert pipeline.recipe_id=='swe_next'
    cache=base/'campaign/runs'/profile['run_id']/'pulls.json'
    assert json.loads(cache.read_text())==json.loads(raw)
    for n,row in zip(options.pr_numbers,json.loads(raw),strict=True):
        original=root/f'evidence/biopython-broader-pr-intake/pr{n}.json' if n!=5310 else source.parent/'pr5310.json'
        data=json.loads(original.read_text());assert row['head']==data['merge_commit_sha'] and row['url']==data['html_url']
    changed=base/'changed.json';changed.write_bytes(raw+b' ')
    try:prepare(spec,profile,settings,changed,digest)
    except ValueError:pass
    else:raise AssertionError('Altered frozen metadata accepted')
    bad=copy.deepcopy(profile);bad['options']['pr_numbers']=[5308,5316,99999]
    try:prepare(spec,bad,settings,source,digest)
    except ValueError:pass
    else:raise AssertionError('Changed selected PR set accepted')
print('PASS: exact native profile/cache accepted; original allowance retained; altered metadata/selection rejected; no services.')
