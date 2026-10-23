"""Verify only the two original post-bootstrap test calls receive more time."""
import hashlib
import json
from pathlib import Path
from post_check_limits import effective_timeout
ROOT=Path(__file__).resolve().parent
script='cd /workspace && python -m pytest -v mne/'
cmd=['docker','exec','cid','bash','-lc',script]
cases=[(cmd,300,'actions',300),(cmd,300,'smoke',1200),(cmd,300,'commit',300),
       (['docker','run','--rm','image','bash','-lc',script],300,'fresh',1200),
       (['docker','exec','cid','bash','-lc','command -v git'],10,'smoke',10),
       (['docker','commit','cid','tag'],600,'commit',600),(cmd,300,'fresh',300)]
for args,declared,phase,expected in cases:assert effective_timeout(args,declared,phase,script)==expected
report={'scope':'Pure timeout routing only; no shell/Docker execution','cases':len(cases),'actions_unchanged':True,'smoke_and_fresh_seconds':1200,'other_operations_unchanged':True,'model_calls':0,'helper_sha256':hashlib.sha256((ROOT/'post_check_limits.py').read_bytes()).hexdigest()}
(ROOT/'post-check-limit-check.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
