import argparse,json,subprocess,sys,tempfile,hashlib,shlex
from pathlib import Path
from repo2rlenv.spec.recipe_options import R2EGymOptions
r=Path('experiments/21-repo2rlenv');profile=json.loads((r/'r2e-gym-biopython-seqfeature-profile.json').read_text());options=R2EGymOptions.model_validate(profile['options'])
assert options.target==3 and options.max_candidates==10 and options.history_limit==2000
program=shlex.split(profile['options']['install_command'].split(' && python -c ',1)[1]);assert len(program)==1;program=program[0]
parser=argparse.ArgumentParser();parser.add_argument('--fixture',type=Path,required=True);args=parser.parse_args()
fixture=args.fixture.read_bytes();assert hashlib.sha256(fixture).hexdigest()=='a188b26e7d7f9126e1ff4d6f3c4c5db1bd0788c3c5073c9727e9dc4ab504019e'
with tempfile.TemporaryDirectory() as temporary:
 root=Path(temporary)
 for mode in ['regular','symlink']:
  work=root/mode;work.mkdir();(work/'LICENSE.rst').write_text('Synthetic license')
  if mode=='regular':(work/'LICENSE').write_text('Synthetic license')
  else:(work/'LICENSE').symlink_to('LICENSE.rst')
  source=work/'Tests/GenBank/origin_line.gb';source.parent.mkdir(parents=True);source.write_bytes(fixture)
  subprocess.run([sys.executable,'-c',program],cwd=work,check=True)
  assert (work/'LICENSE').is_file() and not (work/'LICENSE').is_symlink()
  assert (work/'LICENSE').read_bytes()==(work/'LICENSE.rst').read_bytes()
  assert (work/'GenBank/origin_line.gb').read_bytes()==fixture
 work=root/'changed-fixture';work.mkdir();(work/'LICENSE.rst').write_text('Synthetic license');(work/'LICENSE').write_text('Synthetic license');source=work/'Tests/GenBank/origin_line.gb';source.parent.mkdir(parents=True);source.write_bytes(b'changed')
 result=subprocess.run([sys.executable,'-c',program],cwd=work,capture_output=True)
 assert result.returncode!=0 and not (work/'GenBank/origin_line.gb').exists()
print('PASS: native options/caps valid; regular/symlink packaging works; changed fixture rejected; original bytes retained. No builds/tests/models.')
