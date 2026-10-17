import importlib.util,json,subprocess,sys,tarfile
from pathlib import Path
root=Path('/home/exedev/.codex/worktrees/86a8/biotasks/experiments/21-repo2rlenv')
out=Path('/tmp/biotasks21-private/lcc-control-preparation')
out.mkdir(exist_ok=False)
prefix='native/validation/tasks/e4027e396d2357882bc7/swe-smith-e4027e396d2357882bc7/'
with tarfile.open('/tmp/biotasks21-private/biopython-smith-controls-02/native-evidence.tar.gz',mode='r|gz') as archive:
 for member in archive:
  if not member.name.startswith(prefix):continue
  relative=Path(member.name[len(prefix):])
  if relative.is_absolute() or '..' in relative.parts:raise ValueError('Unexpected path')
  if member.isdir():continue
  if not member.isfile() or member.size>50*1024**2:raise ValueError('Unexpected asset')
  target=out/'original'/relative
  target.parent.mkdir(parents=True,exist_ok=True)
  target.write_bytes(archive.extractfile(member).read())
  target.chmod(member.mode)
subprocess.run([sys.executable,str(root/'prepare_lcc_independent_controls.py'),'--task',str(out/'original'),'--output',str(out/'bundles')],check=True)
spec=importlib.util.spec_from_file_location('controls',root/'prepare_lcc_independent_controls.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
namespace={}
exec('def lcc_mult(seq,wsize):\n'+''.join('    '+line+'\n' for line in m.CASES['equivalent_entropy'][0].splitlines()),namespace)
f=namespace['lcc_mult']
expected=[1,.9927,.9927,1,.9927,.9854,.9927,.9927,.9927,.9794,.9794,.9794,.9794]
actual=f('ATGCGTATCGATCGCGATACGATTAGGCGGAT',20)
assert len(actual)==13 and max(abs(a-b) for a,b in zip(actual,expected))<.0001
assert f('AAAA',2)==[0.,0.,0.]
assert f('acgt',4)==[1.]
assert f('AACC',2)==[0.,.5,0.]
print(json.dumps({'stage':'prepared_not_remotely_executed','cases':list(m.CASES),'arithmetic_checks_passed':True,'source':'preserved native export'}))
