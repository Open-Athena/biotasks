#!/bin/bash
set -euo pipefail
mkdir -p /logs/verifier
python3 - <<'PY'
import json,socket,urllib.request
from pathlib import Path
probes={}
for label,host in [('ip1','1.1.1.1'),('ip2','8.8.8.8')]:
 try:
  with socket.create_connection((host,443),timeout=3):probes[label]='reachable'
 except OSError as error:probes[label]=type(error).__name__
try:
 with urllib.request.urlopen('https://example.com',timeout=3):probes['https']='reachable'
except Exception as error:probes['https']=type(error).__name__
Path('/logs/verifier/network.json').write_text(json.dumps(probes))
if 'reachable' in probes.values():raise RuntimeError('Verifier network isolation failed')
try: passed=json.loads(Path('/output/result.json').read_text())=={'sum':10}
except (OSError,ValueError):passed=False
Path('/logs/verifier/reward.txt').write_text(str(int(passed)))
PY
