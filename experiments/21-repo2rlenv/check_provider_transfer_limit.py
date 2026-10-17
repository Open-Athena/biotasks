import sys,tempfile,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from package_provider_task import pack,unpack
with tempfile.TemporaryDirectory() as tmp:
 p=Path(tmp);task=p/'input';task.mkdir();(task/'data').write_bytes(b'x'*(4*1024**2+1));m=pack(task,p/'bundle.tar.gz');(p/'manifest.json').write_text(json.dumps(m))
 try:unpack(p/'bundle.tar.gz',p/'manifest.json',p/'rejected')
 except AssertionError:pass
 else:raise AssertionError('Oversized transfer accepted without allowance')
 assert not (p/'rejected').exists()
 unpack(p/'bundle.tar.gz',p/'manifest.json',p/'accepted',maximum_bytes=5*1024**2)
 assert (p/'accepted/task/data').stat().st_size==4*1024**2+1
 try:unpack(p/'bundle.tar.gz',p/'manifest.json',p/'excess',maximum_bytes=385*1024**2)
 except ValueError:pass
 else:raise AssertionError('Excessive allowance accepted')
print('PASS: default size rejection, explicit bounded transfer, and hard ceiling')
