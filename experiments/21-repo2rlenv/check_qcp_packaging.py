"""Check packaging only; arguments are public GitHub license and fixture blob JSON files."""
import base64,json,shlex,subprocess,tempfile,hashlib,sys
from pathlib import Path
r=Path(__file__).resolve().parent;rows=[]
license_bytes=base64.b64decode(json.loads(Path(sys.argv[1]).read_text())['content'])
fixture=base64.b64decode(json.loads(Path(sys.argv[2]).read_text())['content'])
for name in ['swe-gen','swe-next','r2e-gym']:
 p=r/(name+'-biopython-profile.json');d=json.loads(p.read_text());command=shlex.split(d['options']['install_command'].split(' && python -c ')[1]);assert len(command)==1
 with tempfile.TemporaryDirectory() as tmp:
  base=Path(tmp);(base/'LICENSE.rst').write_bytes(license_bytes);(base/'LICENSE').symlink_to('LICENSE.rst')
  fp=base/'Tests/PDB/1A8O.pdb';fp.parent.mkdir(parents=True);fp.write_bytes(fixture)
  sentinel=base/'source.py';sentinel.write_text('unchanged source sentinel\n')
  subprocess.run([sys.executable,'-c',command[0]],cwd=base,check=True)
  assert (base/'LICENSE').read_bytes()==license_bytes and not (base/'LICENSE').is_symlink()
  assert (base/'PDB/1A8O.pdb').read_bytes()==fixture==fp.read_bytes()
  fp.unlink()
  subprocess.run([sys.executable,'-c',command[0]],cwd=base,check=True)
  assert (base/'PDB/1A8O.pdb').read_bytes()==fixture
  assert sentinel.read_text()=='unchanged source sentinel\n'
  assert not any(x.is_symlink() for x in base.rglob('*'))
 rows.append({'profile':p.name,'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'packaging_check':'pass'})
(r/'evidence/history-biopython-preparation/packaging-checks.json').write_text(json.dumps({'stage':'local_document_and_fixture_copy_only','records':rows,'models':0,'workers':0,'native_build_or_test_execution':False},indent=2)+'\n')
print('Three packaging commands preserve pinned license and fixture bytes, with no remaining symlinks in the bounded fixtures.')
