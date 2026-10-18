"""Read all retained issue-21 controller attempts; omit addresses, env and archive URIs."""
import argparse
import datetime
import hashlib
import json
from pathlib import Path

from iris.cli.connect import connect_controller
from iris.client.client import IrisClient
from iris.cluster.types import JobName

PREFIX='/exedev/biotasks21-'


def stamp(value):
    if value is None:return None
    text=str(value)
    if text.startswith('Timestamp(') and text.endswith(')'):text=text[10:-1]
    result=datetime.datetime.fromisoformat(text.replace('Z','+00:00'))
    return result if result.tzinfo else result.replace(tzinfo=datetime.timezone.utc)


def span(value):
    start,end=stamp(value.started_at),stamp(value.finished_at)
    return {'state':value.state.name,'started_utc':start.isoformat() if start else None,
            'finished_utc':end.isoformat() if end else None,
            'reported_wall_seconds':(end-start).total_seconds() if start and end else None,
            'exit_code':value.exit_code if end else None}


def collect(exp,private,workspace):
    jobs={};examined=0
    public=list((exp/'evidence').glob('*/submission.json'))+list((exp/'evidence').glob('*/local-controller.json'))
    private_sources=[x for x in private.glob('*job*.json') if not any(word in x.name for word in ('output-location','observation'))]
    for source in sorted(public+private_sources):
        if source.stat().st_size>2*1024**2:continue
        data=source.read_bytes();record=json.loads(data);examined+=1
        if not isinstance(record,dict):continue
        identity=record.get('job_id')
        if not isinstance(identity,str) or not identity.startswith(PREFIX):continue
        origin={'path':str(source.relative_to(exp)) if source in public else source.name,
                'origin':'public_evidence' if source in public else 'private_campaign_receipt','sha256':hashlib.sha256(data).hexdigest()}
        jobs.setdefault(identity,[]).append(origin)
    records=[]
    with connect_controller(config_file=workspace/'lib/iris/config/marin.yaml') as endpoint:
        with IrisClient.remote(endpoint.url,credentials=endpoint.credentials,workspace=workspace) as client:
            discovered=client.list_jobs(prefix=PREFIX,limit=None)
            for job in discovered:jobs.setdefault(str(job.job_id),[])
            for identity,sources in sorted(jobs.items()):
                row={'job_id':identity,'submission_sources':sources,'observed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
                try:
                    tasks=[]
                    for task in client.list_tasks(JobName.from_string(identity)):
                        attempts=[]
                        for attempt in task.attempts:
                            archive=attempt.output_archive
                            attempts.append({'attempt_number':attempt.attempt_number,**span(attempt),
                                             'output_archive':{'state':str(archive.state),'bytes':archive.size_bytes,'sha256':archive.sha256,'ttl_days':archive.ttl_days} if archive else None})
                        tasks.append({'task_id':str(task.task_id),'current_attempt_number':task.current_attempt_number,**span(task),'attempts':attempts,
                                      'retained_attempt_count':len(attempts),'current_span_only':bool(task.started_at and not attempts)})
                    row.update(status='observed',tasks=tasks)
                except Exception as exc:row.update(status='unavailable',error_type=type(exc).__name__)
                records.append(row)
    complete=[a for r in records for t in r.get('tasks',[]) for a in t['attempts'] if a['reported_wall_seconds'] is not None]
    active=[{'job_id':r['job_id'],'task_id':t['task_id'],'state':t['state']} for r in records for t in r.get('tasks',[]) if t['finished_utc'] is None and t['started_utc'] is not None]
    return {'stage':'scoped_retained_controller_timing_inventory','observed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'job_prefix':PREFIX,
            'metadata_files_examined':examined,'server_discovered_jobs':len(discovered),'job_handles':len(jobs),'observed_jobs':sum(x['status']=='observed' for x in records),'unavailable_jobs':[x['job_id'] for x in records if x['status']!='observed'],
            'finished_attempts_with_spans':len(complete),'sum_finished_controller_attempt_seconds':sum(x['reported_wall_seconds'] for x in complete),'active_tasks':active,'jobs':records,
            'limitations':['All server-retained jobs with the exact issue21 prefix plus matching local receipt IDs are covered; expired/unrecorded names or differently named work remain outside this inventory.',
                           'Attempt wall spans can overlap. Their sum is neither campaign elapsed time, CPU utilization nor verified billed time.',
                           'Separate Daytona worker lifetimes are not inferred from controller spans; missing/active attempt durations remain null.',
                           'Observations are sequential, not an atomic global snapshot. Missing/time-out observations do not prove termination and must not trigger restart.',
                           'Only whitelisted timing/state/archive-size/hash metadata is exported. No environment values, worker addresses, private service routes or output archive URIs.']}


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--private-root',type=Path,required=True);p.add_argument('--workspace',type=Path,required=True);a=p.parse_args();exp=Path(__file__).resolve().parent
    result=collect(exp,a.private_root,a.workspace);folder=exp/'evidence/controller-timing-reconciliation-20261018';folder.mkdir(exist_ok=True)
    (folder/'campaign-controller-times.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ('jobs','limitations')}))
