"""Fresh anonymous object verification before final destructive local cleanup."""

import argparse
import datetime
import hashlib
import importlib.metadata
import json
from pathlib import Path, PurePosixPath
import resource
from tempfile import TemporaryDirectory
import time

from huggingface_hub import HfApi
from huggingface_hub.utils import disable_progress_bars

ROOT = Path(__file__).resolve().parent


def sha(path):
    with path.open('rb') as handle:
        return hashlib.file_digest(handle, 'sha256').hexdigest()


def utc():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--state-dir', type=Path, required=True)
    parser.add_argument('--receipt', type=Path, required=True)
    args = parser.parse_args()
    assert args.state_dir.is_dir()
    cohort = json.loads((ROOT / 'cohort.json').read_text())
    assert len(cohort) == 10, 'Check the original fixed-cohort protocol'
    reviewed = []
    for row in cohort:
        manifest_path = ROOT / 'archives' / (row['slug'] + '-manifest.json')
        receipt_path = ROOT / 'archives' / (row['slug'] + '-receipt.json')
        manifest, receipt = (json.loads(path.read_text()) for path in [manifest_path, receipt_path])
        assert manifest['repo'] == row['repo'] and manifest['ref'] == row['ref']
        assert receipt['bucket'] == 'open-athena/biotasks' and receipt['anonymous_download_verified']
        digest = sha(manifest_path)
        assert digest == receipt['manifest_sha256'] and receipt['prefix'].endswith('/' + digest)
        assert receipt['prefix'].startswith('research/28-catalogued-fields/')
        assert not any('provider-usage-' in entry['path'] or entry['path'].endswith('outputs.tar.zst')
            for entry in manifest['files'])
        reviewed.append((manifest_path, manifest, receipt))
    # All ten original publication receipts must exist before any verification starts.
    disable_progress_bars()
    api = HfApi(token=False)
    started = time.monotonic()
    report = {'started_utc': utc(), 'method': 'Fresh anonymous downloads, one object at a time, with expected size/SHA256 from each committed original manifest. No uploads, models, containers or test execution.',
        'client': 'huggingface_hub ' + importlib.metadata.version('huggingface_hub'),
        'bucket': 'open-athena/biotasks', 'repositories': []}
    with TemporaryDirectory(prefix='final-anonymous-', dir=args.state_dir) as temporary:
        scratch = Path(temporary)
        for manifest_path, manifest, receipt in reviewed:
            objects = [{'path': 'manifest.json', 'bytes': manifest_path.stat().st_size,
                        'sha256': sha(manifest_path)}, *manifest['files']]
            byte_count = 0
            for entry in objects:
                relative = PurePosixPath(entry['path'])
                assert not relative.is_absolute() and '..' not in relative.parts
                destination = scratch / relative
                destination.parent.mkdir(parents=True, exist_ok=True)
                api.download_bucket_files(receipt['bucket'],
                    [(receipt['prefix'] + '/' + str(relative), destination)],
                    raise_on_missing_files=True, token=False)
                assert destination.stat().st_size == entry['bytes'] and sha(destination) == entry['sha256']
                byte_count += entry['bytes']
                destination.unlink()  # Keep redundant verification storage bounded.
            result = {'repo': manifest['repo'], 'prefix': receipt['prefix'],
                'manifest_sha256': receipt['manifest_sha256'], 'verified_objects': len(objects),
                'verified_bytes': byte_count, 'finished_utc': utc()}
            assert len(objects) == receipt['verified_objects']
            report['repositories'].append(result)
            print(json.dumps(result), flush=True)
    report.update(finished_utc=utc(), elapsed_seconds=time.monotonic() - started,
        peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        all_ten_original_snapshots_verified=len(report['repositories']) == 10,
        temporary_readbacks_removed=True,
        total_objects=sum(row['verified_objects'] for row in report['repositories']),
        total_bytes=sum(row['verified_bytes'] for row in report['repositories']))
    args.receipt.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({k: v for k, v in report.items() if k != 'repositories'}, indent=2), flush=True)


if __name__ == '__main__':
    main()
