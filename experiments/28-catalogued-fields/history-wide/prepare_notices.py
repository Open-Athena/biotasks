"""Bounded public root-notice preparation from observed refs, not data eligibility clearance."""

import argparse
import datetime
import hashlib
import json
from pathlib import Path
import re
import time

import requests

ROOT = Path(__file__).resolve().parent


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--slug', required=True)
    parser.add_argument('--snapshot', required=True, type=Path)
    parser.add_argument('--max-seconds', type=int, default=120)
    parser.add_argument('--filename', default='LICENSE', choices=['LICENSE', 'LICENSE.txt', 'LICENSE.md', 'COPYING'])
    args = parser.parse_args()
    selected = next(row for row in json.loads((ROOT.parent / 'cohort.json').read_text()) if row['slug'] == args.slug)
    assert args.snapshot.resolve().is_relative_to((ROOT / 'live-observations').resolve())
    assert args.snapshot.stat().st_size < 8 * 1024**2 and 10 <= args.max_seconds <= 300
    snapshot = json.loads(args.snapshot.read_text())
    assert snapshot['run_id'] == 'biotasks28-history-' + args.slug.lower().replace('__', '-') + '-001'
    refs = {}
    for row in snapshot['validation_ref_uses']:
        event = row['event']
        for ref, role in [(event['base_commit'], 'base'), (row['head_ref'], 'head')]:
            assert re.fullmatch('[0-9a-f]{40}', ref)
            refs.setdefault(ref, []).append({'pr': event['pr'], 'role': role,
                'batch': row['batch'], 'validation': event['validation']})
    destination = ROOT / 'source-notices' / args.slug
    destination.mkdir(exist_ok=True)
    started, rows, pending = time.monotonic(), [], []
    with requests.Session() as session:
        # No GitHub credential, cookie extraction, retry adapter or repository execution.
        session.headers['User-Agent'] = 'biotasks-source-notice-review/1'
        for ref, uses in sorted(refs.items()):
            if time.monotonic() - started >= args.max_seconds:
                pending.append(ref)
                continue
            path = destination / (ref + '--' + args.filename)
            url = 'https://raw.githubusercontent.com/' + selected['repo'] + '/' + ref + '/' + args.filename
            if path.exists():
                assert path.stat().st_size < 256 * 1024
                raw = path.read_bytes()
            else:
                try:
                    with session.get(url, stream=True, timeout=8) as response:
                        if response.status_code != 200:
                            rows.append({'ref': ref, 'source': url, 'http_status': response.status_code,
                                'unavailable': True, 'uses_in_original_validation_records': uses})
                            continue
                        buffer = bytearray()
                        for chunk in response.iter_content(chunk_size=8192):
                            assert len(buffer) + len(chunk) < 256 * 1024
                            buffer.extend(chunk)
                        raw = bytes(buffer)
                    raw.decode('utf8')
                except requests.RequestException as error:
                    rows.append({'ref': ref, 'source': url, 'unavailable': True,
                        'transport_error': type(error).__name__, 'uses_in_original_validation_records': uses})
                    continue
                path.write_bytes(raw)
            rows.append({'ref': ref, 'source': url, 'path': path.name, 'bytes': len(raw),
                'sha256': sha(raw), 'uses_in_original_validation_records': uses})
    stamp = datetime.datetime.now(datetime.timezone.utc)
    report = {'checked_utc': stamp.isoformat(), 'repo': selected['repo'],
        'scope': 'Exact original observed-ref public software root notices only; incomplete live set, final terminal binding and data-specific eligibility required. No model/native/control runs or repairs.',
        'source_sha256': sha(Path(__file__).read_bytes()),
        'native_contract_snapshot': str(args.snapshot), 'native_contract_snapshot_sha256': sha(args.snapshot.read_bytes()),
        'validation_starts_in_snapshot': len(snapshot['validation_ref_uses']),
        'source_notices': rows, 'unfetched_refs_at_walltime_boundary': pending,
        'duration_seconds': time.monotonic() - started,
        'no_credentials_supplied': True, 'one_stream_at_a_time': True}
    output = destination / ('notice-inventory-live-' + stamp.strftime('%Y%m%dT%H%M%SZ') + '.json')
    output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'notice_inventory': str(output), 'unique_refs': len(refs),
        'downloaded_or_preserved': sum('path' in row for row in rows),
        'unavailable': sum(row.get('unavailable', False) for row in rows), 'unfetched': len(pending),
        'distinct_notice_hashes': len({row['sha256'] for row in rows if 'sha256' in row}),
        'notice_bytes': sum(row.get('bytes', 0) for row in rows), 'duration_seconds': report['duration_seconds']}))


if __name__ == '__main__':
    main()
