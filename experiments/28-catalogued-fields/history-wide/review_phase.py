"""Inventory original retained text, patch paths and source refs for human publication review."""

import argparse
from collections import Counter
import datetime
import gzip
import hashlib
import json
from pathlib import Path
import re
import tarfile

ROOT = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--state-dir', required=True, type=Path)
    parser.add_argument('--slug', required=True)
    args = parser.parse_args()
    run = 'biotasks28-history-' + args.slug.lower().replace('__', '-') + '-001'
    phase = args.state_dir / (run + '-results/phase-artifacts.tar.gz')
    roots, paths, signals = Counter(), set(), Counter()
    starts, heads, installs, errors, notice_refs = [], {}, [], [], {}
    expanded = decoded = 0
    with tarfile.open(phase, 'r|gz') as archive:
        for member in archive:
            expanded += member.size
            assert expanded <= 32 * 1024**2
            if not member.isfile():
                continue
            roots[member.name.split('/')[0]] += 1
            assert member.size <= 16 * 1024**2
            raw = archive.extractfile(member).read()
            if member.name.endswith('.gz'):
                import io
                with gzip.GzipFile(fileobj=io.BytesIO(raw)) as source:
                    raw = source.read(16 * 1024**2 + 1)
                assert len(raw) <= 16 * 1024**2
            decoded += len(raw)
            assert decoded <= 128 * 1024**2
            text = raw.decode('utf8')
            for name, pattern in {
                'git_binary_patch': r'GIT binary patch',
                'binary_file_marker_only': r'Binary files .* differ',
                'embedded_image_data_uri': r'data:image/[^;]+;base64,',
                'long_base64_like_run': r'[A-Za-z0-9+/]{4096,}={0,2}',
            }.items():
                signals[name] += len(re.findall(pattern, text))
            if member.name.endswith('/events.jsonl'):
                for line in text.splitlines():
                    if not line.strip():
                        continue
                    event = json.loads(line)
                    if event['event'] == 'validation_start':
                        starts.append(event)
                    if 'exception' in event['event'] or event['event'].endswith('_error'):
                        errors.append(event)
            elif '/discovery-pr-' in member.name:
                value = json.loads(text)
                number = int(re.search(r'pr-(\d+)', member.name)[1])
                heads[number] = value.get('headRefOid')
            elif '/exec-' in member.name:
                value = json.loads(text)
                command = value['command']
                patch_paths = re.findall(r'^diff --git a/(.*?) b/(.*?)$', command, re.M)
                paths.update(b for a, b in patch_paths)
                for path in [b for a,b in patch_paths if 'LICENSE' in b.upper() or 'COPYING' in b.upper()]:
                    notice_refs.setdefault(path, set()).add(int(re.search(r'pr-(\d+)', member.name)[1]))
                if 'pip install -e .' in command and value['result']['duration_sec'] > 1:
                    output = value['result']['stdout'] + value['result']['stderr']
                    installs.append({'member': member.name, 'command': command,
                        'shell_exit': value['result']['exit_code'],
                        'duration_sec': value['result']['duration_sec'],
                        'successful_install_marker': 'Successfully installed' in output,
                        'failed_build_marker': 'Failed building' in output,
                        'output_tail': output[-1400:]})
    refs = {}
    for event in starts:
        for ref, role in [(event['base_commit'], 'base'), (heads.get(event['pr']), 'head')]:
            assert ref and re.fullmatch('[0-9a-f]{40}', ref)
            use = {'pr': event['pr'], 'role': role}
            if use not in refs.setdefault(ref, []):
                refs[ref].append(use)
    value = {'checked_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'scope': 'Read-only bounded text/ref inventory; signals require review and do not establish public eligibility.',
        'source_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'original_phase_sha256': hashlib.sha256(phase.read_bytes()).hexdigest(),
        'regular_members': sum(roots.values()), 'expanded_bytes': expanded,
        'decoded_text_bytes': decoded, 'roots': dict(roots), 'signals': dict(signals),
        'patch_paths': sorted(paths), 'actual_validation_source_refs': refs,
        'embedded_notice_paths': {k: sorted(v) for k,v in notice_refs.items()},
        'bootstrap_editable_installs': installs, 'original_exception_events': errors}
    path = ROOT / 'publication-reviews' / (args.slug + '-phase-census.json')
    path.write_text(json.dumps(value, indent=2) + '\n')
    print(json.dumps({k:v for k,v in value.items() if k not in [
        'patch_paths', 'actual_validation_source_refs', 'original_exception_events', 'bootstrap_editable_installs']}))
    print(json.dumps({'editable_installs': installs}))


if __name__ == '__main__':
    main()
