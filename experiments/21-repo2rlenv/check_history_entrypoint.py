"""Check native pipeline configuration and offline PR-cache use; zero live calls."""
import hashlib,json,tempfile
from pathlib import Path
from unittest.mock import patch
from run_history_recipe import prepare
from repo2rlenv.spec.input import GenerationInput
from repo2rlenv.pipelines.recipes.history import source
root=Path(__file__).resolve().parent
settings=json.loads((root/'glm-generation-adaptation.json').read_text())
pulls=root/'evidence/history-profile-preparation/pulls.json';digest=hashlib.sha256(pulls.read_bytes()).hexdigest()
with tempfile.TemporaryDirectory() as temp:
 for recipe,pipeline_name in [('swe_next','pr_runtime'),('r2e_gym','commit_runtime')]:
  profile=json.loads((root/(recipe.replace('_','-')+'-skbio-profile.json')).read_text())
  campaign=Path(temp)/recipe
  spec=GenerationInput.model_validate({'repo':profile['repo'],'pipeline':{'name':pipeline_name,'recipe':recipe},
   'llm':{'provider':'openai','model':'glm-5.3','endpoint':'https://example.invalid/v1','api_key_env':'FIXTURE','max_concurrent':1,'timeout_sec':1200},
   'execution':{'campaign_dir':str(campaign),'worker_receipt':str(campaign/'worker.json'),'runtime_wheel':'/tmp/fixture.whl','run_id':'fixture','timeout_sec':6600},
   'output':{'destination':str(campaign/'tasks'),'org':'open-athena','dataset_name':'fixture'}})
  pipeline,options=prepare(spec,profile,settings,pulls,digest)
  with patch.object(source,'_run_gh',side_effect=AssertionError('Unexpected GitHub request')):
   config=pipeline.worker_configuration(campaign/'runs/fixture')
  assert config['recipe']==recipe and options.target==3 and options.max_candidates==10
  if recipe=='swe_next':
   assert config['pulls']==json.loads(pulls.read_text())
   try:prepare(spec,profile,settings,pulls,'0'*64)
   except ValueError:pass
   else:raise AssertionError('Changed PR context accepted')
print('PASS: native pipeline options, repository identity and frozen PR cache; zero GitHub/model/worker calls.')
