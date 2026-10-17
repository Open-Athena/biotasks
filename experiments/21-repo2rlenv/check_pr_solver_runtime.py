"""Offline checks of the explicit solver tooling adaptation."""
import os,runpy,sys,tempfile,shutil,json,hashlib
from pathlib import Path
from unittest.mock import patch
root=Path(__file__).resolve().parent;sys.path.insert(0,str(root))
from run_pr_provider_preflight import check_task
source=root/'evidence/pr2633-solver-runtime-preparation'
with patch.dict(os.environ,{'BIOTASKS21_RUNTIME_MANIFEST':str(source/'manifest.json')}):
 check_task(source/'harbor-task',root/'evidence/pr2633-acceptance/acceptance.json')
 with tempfile.TemporaryDirectory() as tmp:
  target=Path(tmp)/'task';shutil.copytree(source/'harbor-task',target)
  p=target/'instruction.md';p.write_text(p.read_text()+'Changed task')
  try:check_task(target,root/'evidence/pr2633-acceptance/acceptance.json')
  except AssertionError:pass
  else:raise AssertionError('Changed task accepted')
print('PASS: exact tooling-only adaptation accepted; changed instruction rejected')
runpy.run_path(str(root/'check_pr_provider_preflight.py'),run_name='__main__')
