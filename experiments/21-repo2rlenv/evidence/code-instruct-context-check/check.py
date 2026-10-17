import hashlib,json,sys
from pathlib import Path
sys.path.insert(0,'/home/exedev/.codex/worktrees/86a8/biotasks/experiments/21-repo2rlenv')
from run_code_instruct_validation import prepare_context
from repo2rlenv.execution.lifecycle import save_record
task=Path('/tmp/biotasks21-private/lcc-control-preparation/original')
context=Path('/tmp/biotasks21-private/code-instruct-build-context-check')
record=prepare_context(task,context)
def digest(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(65536),b''):h.update(b)
 return h.hexdigest()
changed=[];count=0
for p in (task/'environment/source').rglob('*'):
 if p.is_file():
  relative=p.relative_to(task/'environment/source');count+=1
  if digest(p)!=digest(context/'source'/relative):changed.append(str(relative))
assert changed==['Bio/SeqUtils/lcc.py'],changed
assert (context/'source/Bio/SeqUtils/lcc.py').read_bytes()==(task/'solution/reference.py').read_bytes()
record.update(stage='local_build_context_preparation_only',source_files_checked=count,changed_source_files=changed,docker_build_executed=False)
out=Path('experiments/21-repo2rlenv/evidence/code-instruct-context-check');out.mkdir(exist_ok=False)
save_record(out/'checks.json',record);print(json.dumps(record))
