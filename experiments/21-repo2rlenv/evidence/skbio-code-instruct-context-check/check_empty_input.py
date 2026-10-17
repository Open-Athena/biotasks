import json,subprocess,sys
from pathlib import Path
root=Path('/home/exedev/.codex/worktrees/86a8/biotasks/experiments/21-repo2rlenv')
fixture=Path('/tmp/biotasks21-private/code-instruct-empty.json');fixture.write_text(json.dumps({'stage':'authoring_only','records':[]}))
campaign=Path('/tmp/biotasks21-private/must-not-create-empty-validation');assert not campaign.exists()
r=subprocess.run([sys.executable,str(root/'run_smith_controls.py'),'--stage','code-instruct-validation','--issues',str(fixture),'--generation-archive','unused','--source-archive','unused','--worker-name','must-not-create-empty-validation','--campaign',str(campaign)],capture_output=True,text=True)
assert r.returncode==2 and 'before allocating a worker' in r.stderr
assert not campaign.exists()
out=root/'evidence/skbio-code-instruct-context-check/empty-input-check.json'
out.write_text(json.dumps({'stage':'offline_preallocation_check','empty_collection_rejected':True,'exit_code':r.returncode,'campaign_directory_created':False,'model_calls':0,'remote_workers':0},indent=2)+'\n')
print('Empty candidates rejected before source archive access or worker allocation')
