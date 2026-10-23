"""Inspect recorded filter decisions/descriptors without fetching diffs or changing eligibility."""

import argparse
from collections import Counter
import datetime
import gzip
import hashlib
import io
import json
from pathlib import Path
import re
import tarfile

ROOT = Path(__file__).resolve().parent


def sha(path):
    with path.open('rb') as source:
        return hashlib.file_digest(source, 'sha256').hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--state-dir', required=True, type=Path)
    parser.add_argument('--slug', required=True)
    args = parser.parse_args()
    selected = next(r for r in json.loads((ROOT.parent / 'cohort.json').read_text()) if r['slug'] == args.slug)
    run = 'biotasks28-history-' + args.slug.lower().replace('__', '-') + '-001'
    phase = args.state_dir / (run + '-results/phase-artifacts.tar.gz')
    source = ROOT.parent / 'preflight/upstream-source'
    inventory = json.loads((source / 'source-manifest.json').read_text())
    expected = {r['path']:r['sha256'] for r in inventory['files']}
    originals = ['src/repo2rlenv/pipelines/pr_runtime.py', 'src/repo2rlenv/spec/options.py',
        'src/repo2rlenv/log_parsers/__init__.py']
    assert all(sha(source / name) == expected[name] for name in originals)
    descriptors, decisions, expanded = {}, [], 0
    with tarfile.open(phase, 'r|gz') as archive:
        for member in archive:
            expanded += member.size
            assert expanded <= 32 * 1024**2
            if not member.isfile():
                continue
            assert member.size <= 16 * 1024**2
            if member.name.endswith('/events.jsonl'):
                current = None
                for line in archive.extractfile(member):
                    if not line.strip():
                        continue
                    event = json.loads(line)
                    if event['event'] == 'candidate_entered':
                        current = event['pr']
                    elif event['event'] == 'native_decision' and event.get('reason') == 'no_new_test_funcs':
                        assert current is not None and current not in decisions
                        decisions.append(current)
            elif '/discovery-pr-' in member.name and member.name.endswith('.json.gz'):
                raw = archive.extractfile(member).read()
                with gzip.GzipFile(fileobj=io.BytesIO(raw)) as decoded:
                    raw = decoded.read(16 * 1024**2 + 1)
                assert len(raw) <= 16 * 1024**2
                number = int(re.search(r'pr-(\d+)', member.name)[1])
                # Metadata is fetched at native invocation time, so preserve the
                # particular observation used for each filter decision below.
                batch = Path(member.name).parts[1]
                descriptors[(batch, number)] = json.loads(raw)
    # Second event pass binds repeated metadata observations to their original
    # entered invocation rather than assuming all historical descriptors agree.
    rows, extensions = [], Counter()
    with tarfile.open(phase, 'r|gz') as archive:
        for member in archive:
            if not member.isfile() or not member.name.endswith('/events.jsonl'):
                continue
            batch, current = Path(member.name).parts[1], None
            for line in archive.extractfile(member):
                if not line.strip():
                    continue
                event = json.loads(line)
                if event['event'] == 'candidate_entered':
                    current = event['pr']
                elif event['event'] == 'native_decision' and event.get('reason') == 'no_new_test_funcs':
                    descriptor = descriptors[(batch, current)]
                    paths = [r['path'] for r in descriptor.get('files', [])]
                    # This deliberately narrow path census is not a re-run of
                    # the upstream patch classifier and does not infer additions.
                    tests = [p for p in paths if p.startswith(('test/', 'tests/'))]
                    extensions.update(Path(p).suffix or '(none)' for p in tests)
                    rows.append({'batch': batch, 'pr': current, 'retained_test_directory_paths': tests})
    assert len(rows) == len(decisions)
    report = {'checked_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'scope': 'Read-only original decisions and invocation-specific retained descriptors. No diff fetch, filter change, test, model call, eligibility repair or reward assignment.',
        'repo': selected['repo'], 'source_sha256': sha(Path(__file__)),
        'original_phase_sha256': sha(phase),
        'pinned_source_sha256': {name:sha(source / name) for name in originals},
        'original_no_new_test_funcs_decisions': len(decisions),
        'retained_test_path_extension_appearances': dict(extensions), 'decisions': rows,
        'limits': 'Path appearances are neither unique-PR counts nor exact test-patch contents/additions. Full filtered diffs were not retained. No false-negative count or C/Perl task eligibility is inferred. Pinned new-function regex recognizes Python/Go/JS/TS constructs; default require_new_test_funcs is true. Its generic parser dispatcher has no C/CTest/Perl runner.'}
    output = ROOT / 'results' / (args.slug + '-filter-census.json')
    output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ['decisions', 'retained_test_path_extension_appearances']}))


if __name__ == '__main__':
    main()
