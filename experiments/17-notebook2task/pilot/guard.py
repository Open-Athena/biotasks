import datetime,fcntl,json,os,signal,subprocess,sys,time
from pathlib import Path
lock=open('/tmp/exe-codex-local-heavy.lock','w')
try: fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
except BlockingIOError: sys.exit('Shared heavy-work lock held; aborting.')
def available():
 return int(next(x.split()[1] for x in Path('/proc/meminfo').read_text().splitlines() if x.startswith('MemAvailable:')))*1024
estimate=450*1024**2
if os.getloadavg()[0]>=1.5 or available()<max(2.5*1024**3,2*1024**3+estimate):sys.exit('Resource admission failed')
env=os.environ.copy()
for k in ['POLARS_MAX_THREADS','RAYON_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','OPENBLAS_NUM_THREADS','NUMEXPR_NUM_THREADS']:env[k]='1'
start=datetime.datetime.now(datetime.timezone.utc).isoformat();peak=0;reason=None
p=subprocess.Popen(['nice','-n','10','ionice','-c','2','-n','7',*sys.argv[2:]],env=env,start_new_session=True)
try:
 while p.poll() is None:
  stats={}
  for path in Path('/proc').glob('[0-9]*/stat'):
   try:
    fields=path.read_text().rsplit(')',1)[1].split()
    stats[int(path.parent.name)]=(int(fields[1]),int(fields[21])*os.sysconf('SC_PAGE_SIZE'))
   except (OSError,ValueError,IndexError):pass
  owned={p.pid}
  while True:
   expanded=owned | {pid for pid,(parent,_) in stats.items() if parent in owned}
   if expanded==owned:break
   owned=expanded
  rss=sum(stats.get(pid,(0,0))[1] for pid in owned)
  peak=max(peak,rss)
  if available()<2*1024**3 or os.getloadavg()[0]>2.5 or rss>500*1024**2:
   reason='resource threshold';os.killpg(p.pid,signal.SIGTERM);break
  time.sleep(1)
 p.wait(timeout=10)
finally:
 try:os.killpg(p.pid,signal.SIGTERM)
 except ProcessLookupError:pass
record={'start':start,'end':datetime.datetime.now(datetime.timezone.utc).isoformat(),'exit_status':p.returncode,'estimated_peak_mib':450,'sampled_descendant_peak_rss_bytes':peak,'stop_reason':reason,'command':sys.argv[2:]}
Path(sys.argv[1]).write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record));sys.exit(p.returncode or (1 if reason else 0))
