import hashlib,json,sys,tarfile
from pathlib import Path
sys.path.insert(0,'/home/exedev/.codex/worktrees/86a8/biotasks/experiments/21-repo2rlenv')
from run_code_instruct_validation import prepare_context
from repo2rlenv.execution.lifecycle import save_record
task=Path('/tmp/biotasks21-private/skbio-code-instruct-original')
task.mkdir(exist_ok=False)
prefix='native/validation/tasks/3cd37b06ec9a972757c3/swe-smith-3cd37b06ec9a972757c3/'
with tarfile.open('/tmp/biotasks21-private/skbio-smith-controls-02/native-evidence.tar.gz',mode='r|gz') as archive:
 for member in archive:
  if not member.name.startswith(prefix):continue
  relative=Path(member.name[len(prefix):])
  if not (str(relative).startswith('environment/') or str(relative)=='solution/reference.py'):continue
  if member.isdir():continue
  if not member.isfile() or relative.is_absolute() or '..' in relative.parts or member.size>50*1024**2:raise ValueError('Unexpected asset')
  destination=task/relative;destination.parent.mkdir(parents=True,exist_ok=True)
  destination.write_bytes(archive.extractfile(member).read());destination.chmod(member.mode)
context=Path('/tmp/biotasks21-private/skbio-code-instruct-build-context-check')
record=prepare_context(task,context,repo="scikit-bio")
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
assert changed==['skbio/diversity/alpha/_base.py'],changed
assert (context/'source/skbio/diversity/alpha/_base.py').read_bytes()==(task/'solution/reference.py').read_bytes()
record.update(stage='local_build_context_preparation_only',source_files_checked=count,changed_source_files=changed,docker_build_executed=False)
out=Path('experiments/21-repo2rlenv/evidence/skbio-code-instruct-context-check');out.mkdir(exist_ok=False)
save_record(out/'checks.json',record);print(json.dumps(record))
