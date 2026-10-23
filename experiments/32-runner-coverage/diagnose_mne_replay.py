"""Identify stopping stage from verified new replay evidence; no regrading."""
import hashlib
import json
from pathlib import Path
import re
ROOT=Path(__file__).resolve().parent
private=ROOT/'inputs-private/mne-recorded-001'
report=json.loads((ROOT/'mne-recorded-result-001.json').read_text())
receipt=json.loads((ROOT/'mne-recorded-readback-001.json').read_text())
payload=json.loads((ROOT/'inputs-private/mne-case-14445/replay.json').read_text())
calls=[json.loads(line) for line in (private/'docker-calls.jsonl').read_text().splitlines()]
run=next(c for c in calls if c['docker_operation']=='run')
cid=(private/f"call-{run['sequence']:03d}-stdout.txt").read_text().strip()
assert re.fullmatch('[a-f0-9]{64}',cid)
command=' && '.join(payload['test_cmds'])
expected=['docker','exec',cid,'bash','-lc',command]
last=calls[-1]
assert hashlib.sha256(json.dumps(expected).encode()).hexdigest()==last['command_sha256']
assert last['exit_code']==124 and last['timeout_seconds']==300
assert len(report['replay']['steps'])==12 and report['replay']['status']=='matched_recorded_exits'
stdout=(private/f"call-{last['sequence']:03d}-stdout.txt").read_text()
assert hashlib.sha256(stdout.encode()).hexdigest()==last['stdout_sha256']
plain=re.sub(r'\x1b\[[0-9;]*m','',stdout)
progress=re.findall(r'\[\s*(\d+)%\]',plain)
assert not report.get('retained_image_id') and report['cleanup_verified']
result={'scope':'New replay stopping-stage diagnosis, not original-log regrading or task acceptance',
        'actions_matched':12,'expected_exit127_preserved':True,'stopping_stage':'post-bootstrap full-suite smoke',
        'original_test_command':command,'smoke_call_identity_verified':True,'smoke_call':last,
        'last_partial_progress_percent':int(progress[-1]) if progress else None,'smoke_completed':False,
        'image_commit_or_fresh_check_reached':False,'pr14445_validation_started':False,'retained_image':None,
        'owned_resources_removed':True,'archive_sha256':receipt['archive_sha256'],'model_calls':0,
        'limits':['All recorded exit127 values matching does not prove successful installation','Partial progress is not a complete result','Longer post-bootstrap allowance would be a separate timing intervention, not automatic repair']}
(ROOT/'mne-replay-diagnosis.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
