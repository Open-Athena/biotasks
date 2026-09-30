import base64,hashlib,json,subprocess
from pathlib import Path
r=Path('/tmp/bio-discovery-20260929/top200');cache=r/'readmes';cache.mkdir(exist_ok=True)
names=['biolink/biolink-model-toolkit','medspacy/QuickUMLS','jensengroup/propka','ParmEd/ParmEd','TimoLassmann/kalign','microsoft/biodiversity','opensim-org/opensim-core','neurreps/awesome-neural-geometry','baranzinilab/kg_rag','clbarnes/transformnd','CellProfiler/centrosome','Marsilea-viz/marsilea','souvikmajumder26/Multi-Agent-Medical-Assistant','molecularai/aizynthfinder','biocore/improved-octo-waddle','biocore/unifrac-binaries','aspirincode/papers-for-molecular-design-using-DL']
for name in names:
 f=cache/(name.lower().replace('/','__')+'.json')
 if not f.exists():
  p=subprocess.run(['gh','api',f'repos/{name}/readme'],capture_output=True,timeout=30)
  assert p.returncode==0,(name,p.stderr.decode());f.write_bytes(p.stdout)
 d=json.loads(f.read_text());body=base64.b64decode(d['content']).decode(errors='replace');(f.with_suffix('.txt')).write_text(body)
 print(name,d['html_url'],body[:2400].replace('\n',' '),flush=True)
