"""Record a bounded local stage; invoke under the shared flock and thread caps."""
import datetime,hashlib,importlib,json,resource,sys
from pathlib import Path
from acquire import guard,ROOT
guard(True);stage=sys.argv[1];start=datetime.datetime.now(datetime.timezone.utc).isoformat();status=1
try:
 importlib.import_module(stage).main();status=0
finally:
 record={'stage':stage,'start':start,'end':datetime.datetime.now(datetime.timezone.utc).isoformat(),'exit_status':status,'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'estimated_working_set_mib':250,'script_sha256':hashlib.sha256((ROOT/(stage+'.py')).read_bytes()).hexdigest()}
 with (ROOT/'stage-runs.jsonl').open('a') as h:h.write(json.dumps(record)+'\n')
 print(record,flush=True)
