import hashlib,json,sys,tarfile,tempfile
from pathlib import Path
sys.path.insert(0,str(Path('experiments/21-repo2rlenv').resolve()))
from preserve_author_output import preserve
with tempfile.TemporaryDirectory() as temp:
 root=Path(temp);source=root/'source';source.mkdir();(source/'models').mkdir()
 (source/'models/partial.json').write_text('{"status":"dispatched"}')
 (source/'candidates.json').write_text('{"records":[]}')
 receipt=preserve(source,root/'output')
 archive=root/'output/author-evidence.tar.gz'
 assert hashlib.sha256(archive.read_bytes()).hexdigest()==receipt['sha256']
 with tarfile.open(archive) as t:
  assert set(t.getnames())=={'author-output/models/partial.json','author-output/candidates.json'}
  for member in t:
   assert t.extractfile(member).read()==(source/Path(member.name).relative_to('author-output')).read_bytes()
 original=archive.read_bytes()
 try:preserve(source,root/'output')
 except FileExistsError:pass
 else:raise AssertionError('overwrote archive')
 assert archive.read_bytes()==original
 for destination,limit in [(source/'recursive',1000),(root/'oversize',1)]:
  try:preserve(source,destination,max_bytes=limit)
  except ValueError:pass
  else:raise AssertionError('invalid preservation accepted')
 (source/'linked').symlink_to(source/'candidates.json')
 try:preserve(source,root/'linked')
 except ValueError:pass
 else:raise AssertionError('linked evidence accepted')
 result={'stage':'offline_synthetic_recovery_checks','partial_author_output_roundtrip':True,'archive_hash_verified':True,'overwrite_rejected':True,'recursive_destination_rejected':True,'size_bound_enforced':True,'linked_evidence_rejected':True,'model_calls':0,'remote_workers':0,'platform_archive_capture_tested':False}
 out=Path('experiments/21-repo2rlenv/evidence/author-output-recovery-check');out.mkdir(exist_ok=False);(out/'checks.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
