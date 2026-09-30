import subprocess,sys
from pathlib import Path
root=Path('/tmp/bio-discovery-20260929/top100')
for script in ['prepare_cohorts.py','annotate_sources.py','export_rankings.py']:
 with (root/(script+'.log')).open('w') as stream:subprocess.run([sys.executable,str(root/script)],stdout=stream,stderr=subprocess.STDOUT,check=True)
 print('Completed',script,flush=True)
subprocess.run(['uv','run','--no-project','experiments/bio_tasks/01_discovery/analyze_rankings.py','--data-dir','docs/experiments/bio-task-generation/01-discovery/data','--date','2026-09-29'],check=True)
