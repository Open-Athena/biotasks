import datetime,hashlib,json,tarfile,tomllib
from pathlib import Path
p=Path('/tmp/biotasks21-private');e=Path('/home/exedev/.codex/worktrees/86a8/biotasks/experiments/21-repo2rlenv')
records=[]
for run in ('biopython-pr-01','biopython-commit-01','biopython-cve-01'):
 archive=p/run/'native-evidence.tar.gz';expected=json.loads((e/'evidence'/run/'archive.json').read_text())
 assert archive.stat().st_size==expected['bytes']
 with archive.open('rb') as stream:assert hashlib.file_digest(stream,'sha256').hexdigest()==expected['sha256']
 assets={}
 with tarfile.open(archive) as source:
  for member in source:
   rel=Path(member.name)
   if len(rel.parts)<4 or rel.parts[:2]!=('native','tasks') or member.isdir():continue
   assert member.isfile() and member.size<1024**2 and '..' not in rel.parts
   assets[str(Path(*rel.parts[3:]))]={'data':source.extractfile(member).read(),'mode':member.mode & 0o7777}
 metadata=tomllib.loads(assets['task.toml']['data'].decode())['metadata']['repo2env']
 files={name:{'sha256':hashlib.sha256(item['data']).hexdigest(),'mode':oct(item['mode']),'bytes':len(item['data'])} for name,item in assets.items()}
 from_line=next(x for x in assets['environment/Dockerfile']['data'].decode().splitlines() if x.startswith('FROM '))
 assert metadata['reproducibility']['mode']=='local_only' and metadata['reproducibility']['image_visibility']=='private'
 f2p=json.loads(assets['tests/f2p.json']['data']);p2p=json.loads(assets['tests/p2p.json']['data'])
 records.append({'run':run,'pipeline':metadata['pipeline'],'task_id':metadata['pipeline']+'/'+metadata['content_hash'].split(':')[1],
  'repository':metadata['repo'],'base':metadata['ref'],'reference':metadata['reference'],'archive_sha256':expected['sha256'],'native_validation':'verified','native_f2p_count':1,'native_p2p_count':54,
  'exported_f2p_count':len(f2p),'exported_p2p_count':len(p2p),'from_line':from_line,'reproducibility':metadata['reproducibility'],'asset_sha256_modes':files,
  'decision':'not_accepted_for_bounded_pilot','reason_codes':['portable_native_runtime_controls_not_established','independent_valid_alternative_not_established'],
  'limits':['Source inspection and retained native evidence; no new target execution, model call or end-to-end grader diagnostic.','Local image reconstruction is retained; a new portable adaptation is possible but has not been executed.','Missing-evidence verifier fallback is a contract limitation; it is not evidence of an executed solver submission.']})
assert len({x['base'] for x in records})==1
assert len({x['asset_sha256_modes']['tests/verifier.py']['sha256'] for x in records})==1
report={'stage':'legacy_native_export_admission_review','observed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'accepted_tasks':0,'records':records,
 'lineage':'One Biopython historical fix represented through PR5148, fixing commit736c96f37b190732ecca9da80ad0cb9d4967214d and its advisory; three route exports are not three independent problems.',
 'retained_verifier_diagnostic':'evidence/biopython-cve-01/verifier-checks/summary.json','existing_review':'evidence/biopython-cve-01/independent-review.md',
 'distinction':'Native historical test validation remains verified. Independent task admission is not established; this does not invalidate the historical result or prove that a future portable profile cannot pass.',
 'consistency':'The fallback diagnostic alone is not used as an admission rejection: portable accepted PR2633 also retains native reward semantics. These original Biopython bundles have no fresh task-level controls or valid-alternative check.'}
folder=e/'evidence/legacy-biopython-admission-review';folder.mkdir(exist_ok=True);(folder/'review.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'original_archives_verified':3,'shared_verifier':True,'independently_accepted':0,'remote_or_model_calls':0}))
