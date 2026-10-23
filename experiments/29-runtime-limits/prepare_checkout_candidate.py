"""Expose only the pinned bootstrap checkout allowance; default remains 60s."""
import difflib
import hashlib
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parent

def replace_once(text,old,new):
    assert text.count(old)==1
    return text.replace(old,new,1)

runner=(ROOT/'upstream/bootstrap/runner.py').read_text()
assert hashlib.sha256(runner.encode()).hexdigest()=='353027eb87f37881e12ba66a0ee6bb1c82e7cab32670552b5bac849c7dab5ee3'
candidate=replace_once(runner,'    depth: int = 1,\n','    depth: int = 1,\n    checkout_timeout: int = 60,\n')
candidate=replace_once(candidate,'        timeout=60,\n        check=False,\n','        timeout=checkout_timeout,\n        check=False,\n')
candidate=replace_once(candidate,'        _shallow_clone_at_ref(repo.url, repo.ref, token, clone_dir)\n','        _shallow_clone_at_ref(repo.url, repo.ref, token, clone_dir, checkout_timeout=spec.checkout_timeout_seconds)\n')
candidate=replace_once(candidate,'            on_progress=lambda line: _emit("clone_progress", {"detail": line}),\n','            on_progress=lambda line: _emit("clone_progress", {"detail": line}),\n            checkout_timeout=spec.checkout_timeout_seconds,\n')
spec=(ROOT/'upstream/spec/input.py').read_text()
candidate_spec=replace_once(spec,'    max_seconds: int = 1800  # 30-minute timeout per bootstrap\n','    max_seconds: int = 1800  # 30-minute timeout per bootstrap\n    checkout_timeout_seconds: int = Field(default=60, gt=0, strict=True)\n')
out=ROOT/'candidate-checkout';out.mkdir(exist_ok=True)
(out/'runner.py').write_text(candidate);(out/'input.py').write_text(candidate_spec)
patch=''
for name,before,after in [('bootstrap/runner.py',runner,candidate),('spec/input.py',spec,candidate_spec)]:
    patch+=''.join(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile='a/src/repo2rlenv/'+name,tofile='b/src/repo2rlenv/'+name))
(ROOT/'checkout-timeout.patch').write_text(patch)
manifest={'upstream_revision':'27d04ee8203cd5b2f20c3997d13836e5f5b64238','candidate_sha256':hashlib.sha256(patch.encode()).hexdigest(),'default_seconds':60,'comparison_seconds':300,'scope':'Only final checkout allowance; clone/fetch timeouts, source ref and commands unchanged','model_calls':0,'remote_runs':0}
(ROOT/'checkout-candidate.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(json.dumps(manifest))
