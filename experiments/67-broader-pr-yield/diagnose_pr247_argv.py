"""Reconstruct original commands as data; reproduce E2BIG using true, never Docker.

Requires the retained private diff and native observations. The diff can be
retrieved from GitHub at the recorded merged PR head; verify its receipt hash.
Only reviewed pure string helpers are loaded from the frozen upstream source.
No PR code or shell script is executed, and no network/model calls are made.
"""
import ast
import errno
import gzip
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parent
CACHE = ROOT.parents[2]/'48/experiments/48-generation-manifest/inputs-private/installed-proof-004/source-cache'
manifest = json.loads((CACHE/'source-manifest.json').read_text())
assert manifest['revision'] == '27d04ee8203cd5b2f20c3997d13836e5f5b64238'
files = {f['path']:f['sha256'] for f in manifest['files']}
digest = lambda text: hashlib.sha256(text.encode()).hexdigest()
namespace = {'re':re}
for filename, names in [
    ('pipelines/pr_runtime.py', {'_TEST_DIR_NAMES','_DOC_PREFIX_DIRS','_DIFF_HEADER_RE','_path_is_test','split_patch_and_test_patch'}),
    ('pipelines/pr_runtime_validate.py', {'_HEREDOC','_heredoc_apply','_build_stage_script'}),
]:
    relative = 'src/repo2rlenv/'+filename
    text = (CACHE/'source'/relative).read_text()
    assert digest(text) == files[relative]
    nodes = []
    for node in ast.parse(text).body:
        if isinstance(node, ast.FunctionDef) and node.name in names:
            nodes.append(node)
        elif isinstance(node, ast.Assign) and any(isinstance(t,ast.Name) and t.id in names for t in node.targets):
            nodes.append(node)
    exec(compile(ast.Module(body=nodes,type_ignores=[]),filename,'exec'),namespace)

diff_path = ROOT/'inputs-private/dendropy-pr247-diff.txt'
receipt = json.loads((ROOT/'inputs-private/dendropy-pr247-diff-receipt.json').read_text())
assert hashlib.sha256(diff_path.read_bytes()).hexdigest() == receipt['diff_sha256']
assert receipt['head_sha'] == '902d7bb676ceb8b9259c39639948729113136715'
patch, test = namespace['split_patch_and_test_patch'](diff_path.read_text())
observations = ROOT/'inputs-private/run-002/dendropy/runs/generation/generation-source/native-observations'
events = [json.loads(line) for line in (observations/'events.jsonl').open()]
start = next(e for e in events if e['event']=='validation_start' and e['pr']==247)
assert digest(patch)==start['source_patch_sha256'] and digest(test)==start['test_patch_sha256']
pre = namespace['_build_stage_script'](start['base_commit'],apply_patch=None,apply_test_patch=test,test_cmds=start['test_cmds'])
recorded = json.loads(gzip.decompress((observations/'exec-0015-pr-247.json.gz').read_bytes()))['command']
assert pre == recorded
post = namespace['_build_stage_script'](start['base_commit'],apply_patch=patch,apply_test_patch=test,test_cmds=start['test_cmds'])
assert len(post.encode()) == 185691 and digest(post) == 'c509efeb522f1c5061bbe750ed185d959b3911c6e8f1a723f0eee1bd4e510396'
assert subprocess.run(['/usr/bin/true','small'],capture_output=True).returncode == 0
try:
    subprocess.run(['/usr/bin/true',post],capture_output=True)
except OSError as error:
    assert error.errno == errno.E2BIG
    print(json.dumps({'post_script_bytes':len(post.encode()),'errno':error.errno,'name':errno.errorcode[error.errno],'local_page_bytes':os.sysconf('SC_PAGESIZE'),'native_or_model_rerun':False}))
else:
    raise AssertionError('This host did not reproduce the recorded argument-size failure')
