import ast,hashlib,json,sys
from pathlib import Path
from repo2rlenv.github import PullRequestSummary
from repo2rlenv.pipelines.pr_runtime import split_patch_and_test_patch
root=Path('experiments/21-repo2rlenv');d=root/'evidence/skbio-pr-runtime-intake'
v=json.loads((d/'pr2633.json').read_text());pr=PullRequestSummary(**v)
assert pr.base_sha=='71286a24bddff66c82cb25a7ca13441aa13c2f2c' and pr.head_sha=='4c07596c68e8e6c1f51f5ea917e642e933802aa7'
source,tests=split_patch_and_test_patch((d/'pr2633.diff').read_text())
assert 'diff --git a/skbio/stats/composition/_ancombc.py ' in source
assert 'test_estimate_bias_em_underflow' in tests
assert 'diff --git a/skbio/stats/composition/tests/test_ancombc.py ' not in source
for p in [root/'replay_skbio_pr.py',root/'run_smith_controls.py']:ast.parse(p.read_text())
record={'stage':'native_historical_intake_preparation','pr_number':2633,'linked_issue':2631,'base_sha':pr.base_sha,'head_sha':pr.head_sha,'native_patch_split_passed':True,'new_test':'test_estimate_bias_em_underflow','test_path':'skbio/stats/composition/tests/test_ancombc.py','input_hashes':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(d.iterdir()) if p.is_file()},'scientific_reference':'PR reports R ANCOMBC comparison; not independently reproduced here','input_lineage':'Upstream public regression fixture; original biological observation provenance not established','native_execution':False,'model_calls':0,'remote_workers':0}
(d/'checks.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps({k:v for k,v in record.items() if k!='input_hashes'}))
