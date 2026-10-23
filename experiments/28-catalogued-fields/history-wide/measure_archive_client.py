"""Supervise bounded archive work or a small existing-object readback; no native/model work."""

import argparse
from contextlib import nullcontext
import datetime
import fcntl
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import resource
import runpy
import shutil
import signal
import subprocess
import sys
import tarfile
import time

ROOT = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def available():
    return int(next(line.split()[1] for line in Path('/proc/meminfo').read_text().splitlines()
        if line.startswith('MemAvailable:'))) * 1024


def own_peak_kib():
    return int(next(line.split()[1] for line in Path('/proc/self/status').read_text().splitlines()
        if line.startswith('VmHWM:')))


def lightweight_manifest_inputs(state, slug):
    """Only bounded local hashing/scanning, with no upload, qualifies for this path."""
    review = json.loads((ROOT / 'publication-reviews' / (slug + '.json')).read_text())
    source = state / ('biotasks28-history-' + slug.lower().replace('__', '-') + '-001-results')
    paths = [source / name for name in review['reviewed_files']]
    assert all(p.parent == source and p.is_file() for p in paths)
    if sum(p.stat().st_size for p in paths) > 16 * 1024**2:
        return None
    total = 0
    phase = source / 'phase-artifacts.tar.gz'
    with tarfile.open(phase, 'r|gz') as archive:
        for member in archive:
            total += member.size
            if total > 16 * 1024**2:
                return None
    return total


def bounded_publish_manifest(manifest, profile_digest, client_versions=None):
    """Known small streaming transfers under the already measured client profile."""
    if (manifest.get('archive_client_resource_profile_sha256') != profile_digest
            or client_versions != {'huggingface_hub': '1.21.0', 'hf_xet': '1.5.1'}):
        return None
    rows = manifest['files']
    total = sum(row['bytes'] for row in rows)
    phase = [row for row in rows if row['path'] == 'evidence/phase-artifacts.tar.gz']
    if (not rows or len(phase) != 1 or total > 32 * 1024**2
            or any(row['bytes'] < 0 or row['bytes'] > 16 * 1024**2 for row in rows)):
        return None
    expanded = sum(row['bytes'] for row in phase[0]['members'])
    if expanded > 16 * 1024**2:
        return None
    return {'total_object_bytes': total, 'original_phase_expanded_bytes': expanded}


def child(state, action=None, slug=None):
    profile = json.loads((ROOT / 'archive-client-profile.json').read_text())
    os.environ.update(profile['environment'])
    os.environ['HF_XET_CACHE'] = str(state / 'archive-client-cache')
    from huggingface_hub import HfApi
    from huggingface_hub.utils import disable_progress_bars
    import hf_xet
    import importlib.metadata
    config = hf_xet.XetConfig()
    assert config.get('reconstruction.download_buffer_limit') == 64000000
    assert config.get('shard.chunk_index_table_max_size') == 8388608
    assert config.get('client.ac_max_download_concurrency') == 1
    if action:
        sys.argv = [str(ROOT / 'archive_result.py'), action, '--state-dir', str(state), '--slug', slug]
        runpy.run_path(str(ROOT / 'archive_result.py'), run_name='__main__')
        return
    manifest = ROOT / 'archives/samtools__samtools-manifest.json'
    receipt = json.loads((ROOT / 'archives/samtools__samtools-receipt.json').read_text())
    assert sha(manifest) == receipt['manifest_sha256'] and receipt['anonymous_download_verified']
    expected = next(row for row in json.loads(manifest.read_text())['files'] if row['path'] == 'public-eligibility-review.json')
    destination = state / 'archive-client-readback-check' / 'readback.json'
    disable_progress_bars()
    HfApi(token=False).download_bucket_files('open-athena/biotasks',
        [(receipt['prefix'] + '/' + expected['path'], destination)], token=False, raise_on_missing_files=True)
    assert destination.stat().st_size == expected['bytes'] and sha(destination) == expected['sha256']
    report = {'anonymous_byte_readback_verified': True, 'object_bytes': expected['bytes'],
        'object_sha256': expected['sha256'], 'profile_sha256': sha(ROOT / 'archive-client-profile.json'),
        'huggingface_hub': importlib.metadata.version('huggingface_hub'), 'hf_xet': importlib.metadata.version('hf_xet'),
        'parsed_resource_limits': {key: config.get(key) for key in ['reconstruction.download_buffer_limit',
            'reconstruction.download_buffer_size', 'reconstruction.download_buffer_perfile_size',
            'data.max_concurrent_file_downloads', 'data.max_concurrent_file_ingestion',
            'shard.chunk_index_table_max_size', 'client.ac_max_download_concurrency']}}
    (state / 'archive-client-readback-child.json').write_text(json.dumps(report, indent=2) + '\n')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--state-dir', type=Path, required=True)
    parser.add_argument('--child', action='store_true')
    parser.add_argument('--archive-action', choices=['prepare', 'publish'])
    parser.add_argument('--slug')
    parser.add_argument('--max-seconds', type=int, default=120,
        help='Bound archival walltime only, not native/control windows; at most900seconds')
    args = parser.parse_args()
    if args.archive_action:
        assert args.slug in {r['slug'] for r in json.loads((ROOT.parent / 'cohort.json').read_text())}
    if args.child:
        child(args.state_dir, args.archive_action, args.slug); return
    assert bool(args.archive_action) == bool(args.slug)
    assert 30 <= args.max_seconds <= 900
    manifest_bytes = lightweight_manifest_inputs(args.state_dir, args.slug) if args.archive_action == 'prepare' else None
    publish_bounds = None
    measured_client_versions = None
    if args.archive_action == 'publish':
        measured_client_versions = {name: importlib.metadata.version(name) for name in ['huggingface_hub', 'hf_xet']}
        publish_bounds = bounded_publish_manifest(json.loads((ROOT / 'archives' / (args.slug + '-manifest.json')).read_text()),
            sha(ROOT / 'archive-client-profile.json'), measured_client_versions)
    lightweight = manifest_bytes is not None or publish_bounds is not None
    estimate = (200 if publish_bounds else 128 if lightweight else 400) * 1024**2
    assert estimate <= 500 * 1024**2
    assert available() >= max(int(2.5 * 1024**3), estimate + 2 * 1024**3) and os.getloadavg()[0] < 1.5
    with (nullcontext() if lightweight else open('/tmp/exe-codex-local-heavy.lock', 'a')) as lock:
        if not lightweight:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                print('Heavy measurement skipped: lock held. Lightweight campaign continues.'); return
        work = args.state_dir / 'archive-client-readback-check'; assert not work.exists(); work.mkdir()
        started = datetime.datetime.now(datetime.timezone.utc).isoformat(); before = time.monotonic()
        parent_initial_peak = own_peak_kib()
        suffix = (args.slug + '-' + args.archive_action + '-' + datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')) if args.archive_action else 'readback-check'
        log = args.state_dir / ('archive-client-' + suffix + '.log')
        stopped, sampled_peak = None, 0
        with log.open('w') as output:
            command = [sys.executable, '-B', str(Path(__file__).resolve()), '--state-dir', str(args.state_dir), '--child']
            if args.archive_action:
                command += ['--archive-action', args.archive_action, '--slug', args.slug]
            process = subprocess.Popen(command, stdout=output, stderr=subprocess.STDOUT,
                start_new_session=True)
            try:
                while process.poll() is None:
                    status = Path('/proc') / str(process.pid) / 'status'
                    if status.exists():
                        rows = status.read_text().splitlines()
                        rss = next((int(line.split()[1]) for line in rows if line.startswith('VmRSS:')), 0)
                        sampled_peak = max(sampled_peak, rss)
                    if available() < 2 * 1024**3 or os.getloadavg()[0] > 2.5:
                        stopped = 'Node memory/load stop threshold'
                    elif sampled_peak > 480 * 1024:
                        stopped = 'Child RSS leaves insufficient room for supervisor under500MiB'
                    elif time.monotonic() - before > args.max_seconds:
                        stopped = 'Bounded archive-client check walltime'
                    if stopped:
                        os.killpg(process.pid, signal.SIGTERM); break
                    time.sleep(1)
                code = process.wait(timeout=10)
            finally:
                if process.poll() is None:
                    os.killpg(process.pid, signal.SIGKILL); process.wait()
                shutil.rmtree(work)
        peak = resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss
        parent_peak = own_peak_kib()
        report = {'started_utc': started, 'finished_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'duration_seconds': time.monotonic() - before, 'exit_code': code, 'stop_reason': stopped,
            'estimated_working_set_mib': estimate // 1024**2, 'child_peak_rss_kib': peak,
            'resource_classification': ('bounded lightweight streaming transfer' if publish_bounds else
                'bounded lightweight manifest scan' if lightweight else 'intensive archive scan/transfer'),
            'heavy_lock_required': not lightweight, 'bounded_manifest_expanded_bytes': manifest_bytes,
            'bounded_publish_inputs': publish_bounds,
            'measured_client_versions': measured_client_versions,
            'small_transfer_estimate_basis': ('Four same-profile original successful transfers peaked at132720..135168KiBcombined, with one stream and64MBdownload buffer; use200MiBestimate, existing active stop thresholds retained.' if publish_bounds else None),
            'walltime_limit_seconds': args.max_seconds,
            'parent_peak_rss_kib': parent_peak, 'combined_peak_upper_bound_kib': peak + parent_peak,
            'parent_initial_exec_peak_kib': parent_initial_peak,
            'parent_raw_rusage_including_launch_history_kib': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
            'supervisor_peak_source': 'Current-exec /proc/self/status VmHWM; raw launch-history rusage retained separately',
            'source_sha256': sha(Path(__file__)), 'profile_sha256': sha(ROOT / 'archive-client-profile.json'),
            'action': args.archive_action or 'anonymous_readback_check', 'slug': args.slug,
            'readback_working_directory_removed': not work.exists(), 'only_owned_process_group_supervised': True}
        target = (ROOT / 'archives' / (suffix + '-resources.json')) if args.archive_action else ROOT / 'archive-client-measurement.json'
        target.write_text(json.dumps(report, indent=2) + '\n')
        print(json.dumps(report, indent=2))
        assert code == 0 and stopped is None and peak + parent_peak <= 500 * 1024


if __name__ == '__main__':
    main()
