"""Count saved native pytest outcomes with pinned pure functions; never run tests or grade."""

import argparse
import ast
from collections import Counter
import datetime
import gzip
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import re
import tarfile

ROOT = Path(__file__).resolve().parent
BASE = ROOT.parent


def sha(path):
    with path.open('rb') as source:
        return hashlib.file_digest(source, 'sha256').hexdigest()


def pinned_parsers():
    source = BASE / 'preflight/upstream-source'
    manifest = json.loads((source / 'source-manifest.json').read_text())
    expected = {r['path']: r['sha256'] for r in manifest['files']}
    parser = source / 'src/repo2rlenv/log_parsers/pytest_parser.py'
    validate = source / 'src/repo2rlenv/pipelines/pr_runtime_validate.py'
    for path in [parser, validate]:
        assert sha(path) == expected[str(path.relative_to(source))]
    spec = importlib.util.spec_from_file_location('pinned_native_pytest_parser', parser)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    node = next(n for n in ast.parse(validate.read_text()).body
        if isinstance(n, ast.FunctionDef) and n.name == '_slice_test_output')
    namespace = {}; exec(compile(ast.Module(body=[node], type_ignores=[]), str(validate), 'exec'), namespace)
    return module.parse_pytest, namespace['_slice_test_output'], {'pytest_parser': sha(parser), 'native_validation': sha(validate)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--state-dir', type=Path, required=True)
    parser.add_argument('--slug', required=True)
    args = parser.parse_args()
    selected = next(r for r in json.loads((BASE / 'cohort.json').read_text()) if r['slug'] == args.slug)
    run = 'biotasks28-history-' + args.slug.lower().replace('__', '-') + '-001'
    phase = args.state_dir / (run + '-results/phase-artifacts.tar.gz')
    parse, slice_output, source_hashes = pinned_parsers()
    starts, rows = {}, []
    with tarfile.open(phase, 'r|gz') as archive:
        for member in archive:
            if not member.isfile() or not member.name.endswith('/events.jsonl'):
                continue
            assert member.size <= 16 * 1024**2
            batch = Path(member.name).parts[1]
            for line in archive.extractfile(member):
                if not line.strip():
                    continue
                event = json.loads(line)
                if event['event'] == 'validation_start':
                    starts[(batch, event['validation'])] = event
    expanded = 0
    with tarfile.open(phase, 'r|gz') as archive:
        for member in archive:
            expanded += member.size
            assert expanded < 64 * 1024**2, 'Use appropriately sized analysis for larger originals'
            found = re.search(r'^native-observations/(batch-\d+)/validation-(\d+)-pr-(\d+)\.json\.gz$', member.name)
            if not member.isfile() or not found:
                continue
            assert member.size <= 16 * 1024**2
            compressed = archive.extractfile(member).read()
            with gzip.GzipFile(fileobj=io.BytesIO(compressed)) as source:
                raw = source.read(16 * 1024**2 + 1)
            assert len(raw) <= 16 * 1024**2
            outcome = json.loads(raw); start = starts[(found[1], int(found[2]))]
            assert start['pr'] == int(found[3]) and start['language'] == 'python'
            assert any('pytest' in command for command in start['test_cmds'])
            statuses = {stage: parse(slice_output(outcome[stage + '_log'])) for stage in ['pre', 'post']}
            f2p = sorted(t for t,s in statuses['pre'].items() if s in ['FAILED', 'ERROR'] and statuses['post'].get(t) == 'PASSED')
            p2p = sorted(t for t,s in statuses['pre'].items() if s == 'PASSED' and statuses['post'].get(t) == 'PASSED')
            compared = outcome['status'] == 'verified' or outcome['reason'] == 'no fail-to-pass tests after validation'
            if compared:
                assert f2p == outcome['fail_to_pass'] and p2p == outcome['pass_to_pass']
            rows.append({'member': member.name, 'member_sha256': hashlib.sha256(compressed).hexdigest(),
                'pr': start['pr'], 'original_status': outcome['status'], 'original_reason': outcome['reason'],
                'original_set_comparison_applicable': compared,
                'original_f2p_p2p_match': True if compared else None, 'original_test_cmds': start['test_cmds'],
                'stages': {stage: {'parsed_statuses': dict(Counter(statuses[stage].values())),
                    'parsed_count': len(statuses[stage]),
                    'collection_error_marker': bool(re.search(r'errors? during collection', outcome[stage + '_log'], re.I)),
                    'missing_module_marker': 'ModuleNotFoundError' in outcome[stage + '_log'],
                    'attribute_spec_marker': 'AttributeError: __spec__' in outcome[stage + '_log'],
                    'removed_compiled_extensions': re.findall(r'^Removing (.*\.so)$', outcome[stage + '_log'], re.M)}
                    for stage in ['pre', 'post']}})
    output = {'checked_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'scope': 'Original native log census with exact pinned pure parser/slicer; no tests, repairs, normalization, model calls or reward assignment.',
        'repo': selected['repo'], 'source_sha256': sha(Path(__file__)), 'pinned_source_sha256': source_hashes,
        'original_phase_sha256': sha(phase), 'completed_native_pairs': len(rows),
        'pairs_with_pre_collection_errors': sum(row['stages']['pre']['collection_error_marker'] for row in rows),
        'pairs_with_post_collection_errors': sum(row['stages']['post']['collection_error_marker'] for row in rows),
        'pairs_with_removed_compiled_extensions': sum(any(v['removed_compiled_extensions'] for v in row['stages'].values()) for row in rows),
        'outcomes': rows}
    (ROOT / 'results' / (args.slug + '-native-pytest-census.json')).write_text(json.dumps(output, indent=2) + '\n')
    print(json.dumps({k:v for k,v in output.items() if k != 'outcomes'}, indent=2))


if __name__ == '__main__':
    main()
