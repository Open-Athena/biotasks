"""Audit downloaded saved-export artifacts; never change tasks or rewards."""
import argparse,datetime,hashlib,json,re,shutil,tarfile
from pathlib import Path
parser=argparse.ArgumentParser()
parser.add_argument('--state-dir', type=Path, required=True)
args=parser.parse_args()
root=Path(__file__).resolve().parent.parent;state=args.state_dir;run='biotasks27-anndata-controls-002'
src=state/(run+'-results');dest=root/'evidence/anndata-controls-002';expanded=src/'expanded';expanded.mkdir(exist_ok=True)
with tarfile.open(src/'phase-artifacts.tar.gz') as archive:
 total=0
 for m in archive:
  if not m.isfile():continue
  path=Path(m.name);assert not path.is_absolute() and '..' not in path.parts
  total+=m.size;assert m.size<20*1024**2 and total<200*1024**2
  p=expanded/path;p.parent.mkdir(parents=True,exist_ok=True)
  with archive.extractfile(m) as inp,p.open('wb') as out:shutil.copyfileobj(inp,out,1024*1024)
for p in [*src.glob('*'),*expanded.rglob('*')]:
 if p.is_file() and p.suffix not in {'.gz','.zst'}:
  assert not re.search(rb'(?:github_pat_|ghp_)[A-Za-z0-9_]{20,}|sk-or-v1-[A-Za-z0-9]{20,}',p.read_bytes()),p
expected=json.loads((root/'controls-followup/task-input-sha256.json').read_text())
for relative,digest in expected.items():
 p=expanded/'published'/Path(relative).relative_to('generated/tasks')
 assert hashlib.sha256(p.read_bytes()).hexdigest()==digest,(relative,'remote task bytes changed')
 assert hashlib.sha256((root/relative).read_bytes()).hexdigest()==digest
rec=json.loads((state/(run+'-terminal.json')).read_text());assert rec['readback_verified'];assert rec['supervisor']['cleanup']['verified_empty']
dest.mkdir(parents=True,exist_ok=True)
for p in src.iterdir():
 if p.is_file() and p.name!='outputs.tar.zst':shutil.copyfile(p,dest/p.name)
parse=lambda s:datetime.datetime.fromisoformat(s.removeprefix('Timestamp(').removesuffix(')'))
a=rec['attempts'][0]
account={'run_id':run,'state':rec['state'],'started_at':str(parse(a['started_at'])),'finished_at':str(parse(a['finished_at'])),'allocated_cpu':4,'allocated_cpu_hours':(parse(a['finished_at'])-parse(a['started_at'])).total_seconds()*4/3600,'archive_bytes':a['output_archive']['size_bytes'],'archive_sha256':a['output_archive']['sha256'],'readback_verified':True,'cleanup_verified_empty':True}
rows=[]
for p in sorted((expanded/'jobs/saved').glob('*/*/result.json')):
 r=json.loads(p.read_text());details_path=p.parent/'verifier/reward-details.json'
 details=json.loads(details_path.read_text()) if details_path.exists() else None
 row={k:r.get(k) for k in ['trial_name','started_at','finished_at','verifier','verifier_result','exception_info']}
 row.update(task=p.parent.parent.name.rsplit('-',1)[0],agent=p.parent.parent.name.rsplit('-',1)[1],path=str(p.relative_to(expanded)),reward_details=details)
 rows.append(row)
assert len(rows)==4 and {(r['task'],r['agent']) for r in rows}=={(t,a) for t in ['scverse__anndata-2634','scverse__anndata-2652'] for a in ['nop','oracle']}
audit={'source_checkpoint':'f1afcca4','method':'Fresh reconstruction of saved upstream bootstrap Dockerfile; original twenty task files unchanged; no generation or repair','llm_calls':0,'task_files_unchanged':True,'trials':rows,'accounting':account,'verified_count':0}
for task in sorted(set(r['task'] for r in rows)):
 selected=[r for r in rows if r['task']==task];by_agent={r['agent']:r for r in selected}
 nop=(by_agent.get('nop',{}).get('reward_details') or {});oracle=(by_agent.get('oracle',{}).get('reward_details') or {})
 verified=nop.get('reward')==0 and oracle.get('reward')==1 and nop.get('parse_status')=='ok' and oracle.get('parse_status')=='ok'
 audit.setdefault('tasks',[]).append({'task':task,'verified_tracked':verified,'oracle_command_resolved':oracle.get('command_resolved')})
 audit['verified_count']+=int(verified)
(dest/'independent-control-audit.json').write_text(json.dumps(audit,indent=2)+'\n')
(dest/'readback.json').write_text(json.dumps({**account,'source_checkpoint':'f1afcca4','publication_review':'AnnData BSD-3-Clause source/task patches previously reviewed; no biological datasets, environments or images retained. Own build/control logs and metadata inspected; credential-pattern scan passed.','retention':'Permanent research branch while conclusions depend on it'},indent=2)+'\n')
manifest={str(p.relative_to(dest)):{'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted(dest.rglob('*')) if p.is_file() and p.name!='manifest.json'}
(dest/'manifest.json').write_text(json.dumps({'files':manifest,'provenance':'Saved-export control follow-up, checkpoint f1afcca4; original experiments and generated files preserved'},indent=2)+'\n')
print(json.dumps(audit,indent=2))
