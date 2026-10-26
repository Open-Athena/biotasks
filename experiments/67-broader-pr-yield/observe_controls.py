"""Observe only already submitted, unfinished native controls; no job admission."""
from datetime import datetime,timezone
import json
from pathlib import Path
from biotasks.validation import bridge

root=Path(__file__).resolve().parent
active=json.loads((root/'active-workflow.json').read_text());work=root/active['work_dir']
rows=[]
for case in ['nibabel','dendropy','anndata','biopython']:
    val=work/(case+'-handoff')/'validation';f=val/'plan.json'
    if not f.exists():continue
    plan=json.loads(f.read_text())
    for group in plan['tasks']:
        d=val/'runs'/group['id'];submission=d/'submission.json';journal=d/'journal.json'
        if not submission.exists() or not journal.exists():continue
        j=json.loads(journal.read_text())
        if any(s['stage']=='remote_terminal' for s in j['stages']):continue
        value=bridge.call(plan['backend'],{'action':'observe','group':group},root/'inputs-private/control-observe.log')
        rows.append({'case':case,'task':group['task']['task'],'observation':value})
        break
    if rows:break
value={'observed_utc':datetime.now(timezone.utc).isoformat(),'existing_controls':rows,'new_submissions':0,'new_model_calls':0}
stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
(root/f'control-observation-{stamp}.json').write_text(json.dumps(value,indent=2)+'\n')
print(json.dumps(value,indent=2))
