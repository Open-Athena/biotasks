"""One sequential bounded Codex trial; invoke inside the shared resource guard."""
import datetime
import json
from pathlib import Path
import shutil
import subprocess
import sys

root = Path(__file__).resolve().parents[1]
name = sys.argv[1]
assert name in {'seta-cytopathology', 'seta-cytopathology-retry', 'bix-asxl1', 'seta-builder'}
run = root/'runs/20261006-seta-v1-pilot'/name
work = Path('/tmp/biotasks17-pilot')/name
assert not (run/'events.jsonl').exists(), 'Append-only trial: choose a new run before retrying.'
policy = 'Stage 1 pilot only: inspect staged source files and write the requested draft specification. This restriction applies ONLY to actions you execute now, not to the requirements or viability of the task you propose: you may design tasks that require model training, R/Python packages and biological computation, but do not run those analyses during this idea-only authoring stage. Do not install packages, use Docker, access network services, launch agents, or read credentials. Keep shell work bounded below 100 MiB. Work only with the stated seed and output paths. External services and subsequent builder execution are outside this trial.'
if name == 'seta-builder':
    policy = 'This authoring host cannot execute scientific analyses or build/run containers. You may write the full task package and scripts for later validation; proposed target tasks may require scientific computation. Do not train models now, install packages, run Docker/Harbor, access network services, read credentials, or launch other agents. Lightweight text/schema checks are allowed below 100 MiB. Do not invent pretrained artifacts, runtime measurements or validation outcomes. Record unavailable execution prerequisites as blocked. The existing draft_spec.md is read-only. Work only in the task directory and read the supplied seed.'
cmd = ['codex', '--no-daemon', '-a', 'never', 'exec', '--ephemeral', '--ignore-user-config', '--skip-git-repo-check', '--json', '--sandbox', 'workspace-write', '-m', 'gpt-6-astra', '-c', 'model_reasoning_effort="medium"', '-c', 'project_doc_max_bytes=0', '-c', 'features.multi_agent=false', '-c', 'developer_instructions='+json.dumps(policy), '-C', str(work), '-o', str(work/'last-message.md'), '-']
start = datetime.datetime.now(datetime.timezone.utc).isoformat()
with (run/'prompt.md').open() as prompt, (run/'events.jsonl').open('w') as out, (run/'stderr.txt').open('w') as err:
    result = subprocess.run(['timeout', '--foreground', '--kill-after=5s', '300', *cmd], stdin=prompt, stdout=out, stderr=err)
for p in work.rglob('*'):
    if p.is_file() and 'example' not in p.relative_to(work).parts:
        relative = p.relative_to(work)
        if p.stat().st_size <= 500_000 and p.suffix not in {'.csv', '.pkl', '.joblib'}:
            target = run/relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(p, target)
record = {'start': start, 'end': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'exit_status': result.returncode, 'command': cmd, 'wall_limit_seconds': 300, 'harness_policy': policy, 'billing': 'Existing ChatGPT login; no API key or paid infrastructure provisioned; monetary cost unavailable', 'status': 'awaiting output inspection'}
(run/'execution.json').write_text(json.dumps(record, indent=2)+'\n')
print(json.dumps({'case':name,'exit_status':result.returncode,'files':[p.name for p in run.iterdir()]}))
