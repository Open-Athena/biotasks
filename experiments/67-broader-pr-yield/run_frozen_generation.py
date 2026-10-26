"""Advance one already-frozen generation while unrelated cleanup waits."""
import argparse,json
from pathlib import Path
from biotasks.generation import run_generation

root=Path(__file__).resolve().parent
parser=argparse.ArgumentParser();parser.add_argument('case',choices=['dendropy','anndata','biopython']);args=parser.parse_args()
active=json.loads((root/'active-workflow.json').read_text());work=root/active['work_dir'];manifest=json.loads((root/active['manifest']).read_text())
case=next(c for c in manifest['cases'] if c['id']==args.case)
assert case['mode']=='fresh'
plan=run_generation.verify(work/args.case)
assert plan['group']['run_id']==case['run_id']
# The unchanged implementation retains all source, reservation, secret,
# existing-handle, native, retention and owner-only cleanup gates.
result=run_generation.run(work/args.case)
(root/f'{args.case}-generation-result.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2),flush=True)
