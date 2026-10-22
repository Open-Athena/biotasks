"""Reconstruct original failed stage strings only; never execute or repair them."""

import argparse
import ast
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent


def original_functions():
    source = ROOT / 'preflight/upstream-source'
    manifest = json.loads((source / 'source-manifest.json').read_text())
    expected = {entry['path']: entry['sha256'] for entry in manifest['files']}
    namespace = {'re': re}
    for relative, names in [
        ('src/repo2rlenv/pipelines/pr_runtime.py', {'_TEST_DIR_NAMES', '_DOC_PREFIX_DIRS',
            '_DIFF_HEADER_RE', '_path_is_test', 'split_patch_and_test_patch'}),
        ('src/repo2rlenv/pipelines/pr_runtime_validate.py',
            {'_HEREDOC', '_heredoc_apply', '_build_stage_script'}),
    ]:
        path = source / relative
        assert hashlib.sha256(path.read_bytes()).hexdigest() == expected[relative]
        nodes = []
        for node in ast.parse(path.read_text()).body:
            name = (node.name if isinstance(node, ast.FunctionDef) else
                node.targets[0].id if isinstance(node, ast.Assign)
                and isinstance(node.targets[0], ast.Name) else None)
            if name in names:
                nodes.append(node)
        assert len(nodes) == len(names)
        exec(compile(ast.Module(body=nodes, type_ignores=[]), str(path), 'exec'), namespace)
    return namespace


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--results', type=Path, required=True)
    parser.add_argument('--pr', type=int, required=True)
    parser.add_argument('--diff', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    assert args.diff.stat().st_size <= 8 * 1024**2
    raw = args.diff.read_bytes()
    functions = original_functions()
    source, test = functions['split_patch_and_test_patch'](raw.decode())
    events = [json.loads(s) for s in (args.results / 'expanded/native-observations/events.jsonl').read_text().splitlines()]
    start = next(v for v in events if v['event'] == 'validation_start' and v['pr'] == args.pr)
    error = next(v for v in events if v['event'] == 'validation_exception' and v['pr'] == args.pr)
    for name, patch in [('source', source), ('test', test)]:
        assert hashlib.sha256(patch.encode()).hexdigest() == start[name + '_patch_sha256']
    scripts = {stage: functions['_build_stage_script'](start['base_commit'],
        apply_patch=source if stage == 'post' else None,
        apply_test_patch=test, test_cmds=start['test_cmds']) for stage in ['pre', 'post']}
    output = {'method': 'Strings only, using exact unmodified pinned upstream pure functions extracted via AST. No Docker/shell/tests/patch application/model request.',
        'diff_bytes': len(raw), 'diff_sha256': hashlib.sha256(raw).hexdigest(),
        'patch_hashes_match_original_validation_start': True,
        'source_patch_bytes': len(source.encode()), 'test_patch_bytes': len(test.encode()),
        'source_patch_sha256': start['source_patch_sha256'],
        'test_patch_sha256': start['test_patch_sha256'],
        'stage_script_bytes': {stage: len(script.encode()) for stage, script in scripts.items()},
        'original_observed_exception': error,
        'patch_paths': re.findall(r'^diff --git a/(\S+) b/(\S+)$', raw.decode(), re.M)}
    args.output.write_text(json.dumps(output, indent=2) + '\n')
    print(json.dumps({k: v for k, v in output.items() if k != 'patch_paths'}, indent=2))


if __name__ == '__main__':
    main()
