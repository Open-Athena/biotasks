"""Read-only terminal attempt accounting and archive identity for original handle."""
import argparse
import dataclasses
import json
from pathlib import Path
from iris.cli.connect import connect_controller
from iris.client.client import IrisClient
from iris.cluster.types import JobName
from iris.resources.state import is_job_finished

ROOT=Path(__file__).resolve().parent
p=argparse.ArgumentParser();p.add_argument('--config',required=True,type=Path);args=p.parse_args()
with connect_controller(config_file=args.config) as endpoint:
    with IrisClient.remote(endpoint.url,credentials=endpoint.credentials,timeout_ms=30000) as client:
        job=client.job(JobName.from_string('/exedev/biotasks31-macs-longcheck-001'))
        status=job.status()
        if not is_job_finished(status.state):
            print(json.dumps({'job_id':str(job.job_id),'state':str(status.state)}));raise SystemExit(0)
        task=job.task(0);detail=task.describe();attempts=detail.status.attempts
        assert len(attempts)==1
        a=attempts[0];seconds=a.finished_at.epoch_seconds()-a.started_at.epoch_seconds()
        archive=dataclasses.asdict(a)['output_archive']
        report={'job_id':str(job.job_id),'state':str(status.state),'attempts':1,'exit_code':a.exit_code,'allocated_cpu':detail.resources.cpu_millicores/1000,'attempt_seconds':seconds,'allocated_cpu_hours':seconds*detail.resources.cpu_millicores/1000/3600,'output_archive':archive,'model_calls':0}
        (ROOT/'macs-longcheck-accounting.json').write_text(json.dumps(report,indent=2,default=str)+'\n')
        print(json.dumps(report,default=str))
