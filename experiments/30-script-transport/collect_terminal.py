"""Read-only original-handle audit for the three explicit synthetic probe revisions."""
import argparse
import hashlib
import json
from pathlib import Path
from iris.cli.connect import connect_controller
from iris.client.client import IrisClient
from iris.cluster.types import JobName
from iris.resources.state import is_job_finished

ROOT=Path(__file__).resolve().parent
parser=argparse.ArgumentParser();parser.add_argument('--config',required=True,type=Path);args=parser.parse_args()
rows=[]
with connect_controller(config_file=args.config) as endpoint:
    with IrisClient.remote(endpoint.url,credentials=endpoint.credentials,timeout_ms=30000) as client:
        for suffix in sorted(x.name.rsplit('-',1)[1] for x in (ROOT/'run-private').iterdir() if (x/'submission.json').exists()):
            name='biotasks30-transport-'+suffix
            submission=json.loads((ROOT/'run-private'/name/'submission.json').read_text())
            job=client.job(JobName.from_string('/exedev/'+name))
            status=job.status();assert is_job_finished(status.state)
            tasks=[]
            for task in job.tasks():
                st=task.status();description=task.describe()
                assert len(st.attempts)==1
                a=st.attempts[0]
                duration=(a.finished_at.epoch_seconds()-a.started_at.epoch_seconds()) if a.started_at and a.finished_at else None
                tasks.append({'state':str(st.state),'attempts':len(st.attempts),'exit_code':a.exit_code,
                              'started_utc':a.started_at.as_formatted_date() if a.started_at else None,
                              'finished_utc':a.finished_at.as_formatted_date() if a.finished_at else None,
                              'allocated_cpu':description.resources.cpu_millicores/1000,
                              'attempt_seconds':duration,
                              'allocated_attempt_cpu_hours':duration*description.resources.cpu_millicores/1000/3600 if duration is not None else None})
            logs=job.logs(max_lines=100,tail=True)
            raw=next(e.data for e in logs if e.data.startswith('BIOTASKS30_RESULT='))
            result=json.loads(raw.split('=',1)[1])
            dest=ROOT/'attempts'/suffix;dest.mkdir(parents=True,exist_ok=True)
            if (dest/'result.json').exists():assert json.loads((dest/'result.json').read_text())==result
            else:(dest/'result.json').write_text(json.dumps(result,indent=2)+'\n')
            (dest/'result-log.txt').write_text(raw+'\n')
            if suffix in ('003','004'):
                assert result['completed'] and result['cleanup']['owned_containers_absent'] and result['tool_files_removed']
            rows.append({'job_id':str(job.job_id),'state':str(status.state),'tasks':tasks,
                         'checkpoint':submission['checkpoint'],'payload_sha256':submission['payload_sha256'],
                         'result_log_sha256':hashlib.sha256((raw+'\n').encode()).hexdigest(),
                         'result_path':str((dest/'result.json').relative_to(ROOT))})
all_times=[t['allocated_attempt_cpu_hours'] for row in rows for t in row['tasks']]
report={'scope':'All submitted original probe handles; no resubmission; synthetic Docker evidence, not PR recovery',
        'runs':rows,'all_terminal':True,'one_attempt_each':True,
        'allocated_attempt_cpu_hours':sum(all_times) if all(x is not None for x in all_times) else None,
        'model_calls':0,'model_cost_usd':0,'new_capacity':False,
        'cleanup':'001 failed before first Docker process/container creation; 002/003/004 results verify owned containers absent and tool files removed. Shared immutable input image retained.'}
(ROOT/'probe-accounting.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'all_terminal':True,'allocated_attempt_cpu_hours':report['allocated_attempt_cpu_hours'],'model_calls':0}))
