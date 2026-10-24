"""Reuse upstream static asset validation as a diagnostic; never alter tasks."""
from dataclasses import asdict
import json
from pathlib import Path
import sys
import tomllib

from common import UPSTREAM,sha,write

ROOT=Path(__file__).resolve().parent


def main():
    plan=json.loads((ROOT/'source-plan.json').read_text());package=Path(plan['upstream_package'])
    acquisition=json.loads(Path(plan['upstream_acquisition']).read_text());assert acquisition['revision']==UPSTREAM
    for row in acquisition['files']:assert sha(package/row['path'])==row['sha256']
    def audit(event,args):
        if event in ('socket.connect','socket.getaddrinfo','subprocess.Popen','os.system'):raise AssertionError(event)
        if event=='open' and isinstance(args[0],str):
            path=str(Path(args[0]).resolve())
            assert not any(s in path for s in ('.codex/secrets/','.config/gh/','.config/coreweave/','.cache/huggingface/token','.git-credentials','.docker/config.json'))
    sys.addaudithook(audit);sys.path[:0]=[str(package/'src'),plan['upstream_extra_modules']]
    from repo2rlenv.validation import validate_task
    cohort=json.loads((ROOT/'cohort.json').read_text());rows=[]
    for family in cohort['families']:
        for task in family['tasks']:
            root=ROOT/'inputs-private/frozen'/family['id']/'tree/outputs'/family['id']/task['task']
            for spec in task['files']:assert sha(ROOT/'inputs-private/frozen'/family['id']/'tree'/spec['path'])==spec['sha256']
            findings=validate_task(root,tomllib.loads((root/'task.toml').read_text()),oracle=True)
            rows.append(dict(task=task['task'],mode=family['mode'],findings=[asdict(f) for f in findings]))
    write(ROOT/'native-static-findings.json',dict(upstream_revision=UPSTREAM,tasks=rows,
        scope='Upstream asset diagnostics only; original Harbor 0.6.6 runtime/controls remain decisive',
        errors=sum(f['severity']=='error' for t in rows for f in t['findings']),
        warnings=sum(f['severity']=='warning' for t in rows for f in t['findings']),model_calls=0,docker_commands=0))
    print(json.dumps(dict(tasks=len(rows),errors=sum(f['severity']=='error' for t in rows for f in t['findings']),
        warnings=sum(f['severity']=='warning' for t in rows for f in t['findings']),model_calls=0)))


if __name__=='__main__':main()
