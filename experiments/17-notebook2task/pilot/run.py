"""One sequential bounded Codex trial; invoke inside the shared resource guard."""
import datetime
import json
from pathlib import Path
import shutil
import subprocess
import sys

root = Path(__file__).resolve().parents[1]
name = sys.argv[1]
assert name in {'seta-cytopathology', 'seta-cytopathology-retry', 'bix-asxl1'}
run = root/'runs/20261006-seta-v1-pilot'/name
work = Path('/tmp/biotasks17-pilot')/name
assert not (run/'events.jsonl').exists(), 'Append-only trial: choose a new run before retrying.'
policy = 'Stage 1 pilot only: inspect staged source files and write the requested draft specification. This restriction applies ONLY to actions you execute now, not to the requirements or viability of the task you propose: you may design tasks that require model training, R/Python packages and biological computation, but do not run those analyses during this idea-only authoring stage. Do not install packages, use Docker, access network services, launch agents, or read credentials. Keep shell work bounded below 100 MiB. Work only with the stated seed and output paths. External services and subsequent builder execution are outside this trial.'
cmd = ['codex', '--no-daemon', '-a', 'never', 'exec', '--ephemeral', '--ignore-user-config', '--skip-git-repo-check', '--json', '--sandbox', 'workspace-write', '-m', 'gpt-6-astra', '-c', 'model_reasoning_effort="medium"', '-c', 'project_doc_max_bytes=0', '-c', 'features.multi_agent=false', '-c', 'developer_instructions='+json.dumps(policy), '-C', str(work), '-o', str(work/'last-message.md'), '-']
start = datetime.datetime.now(datetime.timezone.utc).isoformat()
with (run/'prompt.md').open() as prompt, (run/'events.jsonl').open('w') as out, (run/'stderr.txt').open('w') as err:
    result = subprocess.run(['timeout', '--foreground', '--kill-after=5s', '300', *cmd], stdin=prompt, stdout=out, stderr=err)
for p in work.glob('*'):
    if p.is_file(): shutil.copy2(p, run/p.name)
record = {'start': start, 'end': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'exit_status': result.returncode, 'command': cmd, 'wall_limit_seconds': 300, 'harness_policy': policy, 'billing': 'Existing ChatGPT login; no API key or paid infrastructure provisioned; monetary cost unavailable', 'status': 'awaiting output inspection'}
(run/'execution.json').write_text(json.dumps(record, indent=2)+'\n')
print(json.dumps({'case':name,'exit_status':result.returncode,'files':[p.name for p in run.iterdir()]}))
