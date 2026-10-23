"""Pinned splitter/filter census over predeclared current public diffs; no task run."""
import ast
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent
wanted = {'_DOC_PREFIX_DIRS', '_TEST_DIR_NAMES', '_DIFF_HEADER_RE', '_NEW_TEST_FUNC_RE', '_path_is_test', 'split_patch_and_test_patch', '_count_new_test_funcs'}
tree = ast.parse((ROOT / 'upstream/pipelines/pr_runtime.py').read_text())
nodes = []
for node in tree.body:
    if isinstance(node, ast.FunctionDef):
        names = [node.name]
    elif isinstance(node, ast.Assign):
        names = [t.id for t in node.targets if isinstance(t, ast.Name)]
    elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
        names = [node.target.id]
    else:
        names = []
    if set(names) & wanted:
        nodes.append(node)
namespace = {'re': re}
exec(compile(ast.Module(body=nodes, type_ignores=[]), 'pinned_filter', 'exec'), namespace)
acquired = {r['pr']: r for r in json.loads((ROOT / 'sample-acquisition.json').read_text())}
results = []
for row in json.loads((ROOT / 'sample.json').read_text())['rows']:
    pr = row['pr']
    item = acquired[pr]
    if 'sha256' not in item['diff']:
        results.append({'pr': pr, 'status': 'unavailable'})
        continue
    raw = (ROOT / item['diff']['local_path']).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == item['diff']['sha256']
    source, test = namespace['split_patch_and_test_patch'](raw.decode())
    additions = [line[1:] for line in test.splitlines() if line.startswith('+') and not line.startswith('+++')]
    deletions = [line[1:] for line in test.splitlines() if line.startswith('-') and not line.startswith('---')]
    paths = re.findall(r'^diff --git a/\S+ b/(\S+)$', test, re.M)
    added_calls = sum(bool(re.match(r'\s*test_cmd\(', line)) for line in additions)
    deleted_calls = sum(bool(re.match(r'\s*test_cmd\(', line)) for line in deletions)
    added_subs = [m.group(1) for line in additions if (m := re.match(r'\s*sub\s+(test_\w+)', line))]
    results.append({'pr': pr, 'source_url': item['current_metadata']['html_url'],
                    'current_head_sha': item['current_metadata']['head_sha'],
                    'diff_sha256': item['diff']['sha256'], 'test_paths': paths,
                    'test_path_set_matches_original_descriptors': set(paths) == set(row['retained_test_directory_paths']),
                    'pinned_recognized_new_test_functions': namespace['_count_new_test_funcs'](test),
                    'added_perl_test_cmd_calls': added_calls, 'deleted_perl_test_cmd_calls': deleted_calls,
                    'net_added_perl_test_cmd_calls': added_calls - deleted_calls,
                    'added_perl_test_subroutines': added_subs})
assert len(results) == 6
out = {'scope': 'Static current public diffs for six predeclared original rejects; no original diff-byte equality or native F2P claim',
       'selection': 'sample.json', 'results': results,
       'four_cases_with_net_added_perl_test_invocations': [r['pr'] for r in results if r.get('net_added_perl_test_cmd_calls', 0) > 0],
       'interpretation': 'The pinned recognizer misses added Perl tests in this sample. Other sampled changes include fixture-only and existing-test edits. This does not estimate task yield or assert all 219 rejects are false negatives.',
       'retention': 'Raw diffs/metadata retained locally in ignored inputs-private while referenced; hashes/current source URLs public, no raw biological fixture bytes published.'}
(ROOT / 'sample-findings.json').write_text(json.dumps(out, indent=2)+'\n')
print(json.dumps({'cases': len(results), 'with_net_added_perl_test_calls': out['four_cases_with_net_added_perl_test_invocations'],
                  'all_recognized_zero': all(r.get('pinned_recognized_new_test_functions') == 0 for r in results)}))
