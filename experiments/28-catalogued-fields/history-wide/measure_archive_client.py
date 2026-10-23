"""Bounded anonymous readback measurement, using only an already-published object."""

import argparse
import datetime
import fcntl
import hashlib
import json
import os
from pathlib import Path
import resource
import shutil
import signal
import subprocess
import sys
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


def child(state):
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
    args = parser.parse_args()
    if args.child:
        child(args.state_dir); return
    estimate = 400 * 1024**2
    assert estimate <= 500 * 1024**2
    assert available() >= max(int(2.5 * 1024**3), estimate + 2 * 1024**3) and os.getloadavg()[0] < 1.5
    with open('/tmp/exe-codex-local-heavy.lock', 'a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            print('Heavy measurement skipped: lock held. Lightweight campaign continues.'); return
        work = args.state_dir / 'archive-client-readback-check'; assert not work.exists(); work.mkdir()
        started = datetime.datetime.now(datetime.timezone.utc).isoformat(); before = time.monotonic()
        parent_initial_peak = own_peak_kib()
        log = args.state_dir / 'archive-client-readback-check.log'
        stopped, sampled_peak = None, 0
        with log.open('w') as output:
            process = subprocess.Popen([sys.executable, '-B', str(Path(__file__).resolve()),
                '--state-dir', str(args.state_dir), '--child'], stdout=output, stderr=subprocess.STDOUT,
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
                    elif time.monotonic() - before > 120:
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
            'estimated_working_set_mib': 400, 'child_peak_rss_kib': peak,
            'parent_peak_rss_kib': parent_peak, 'combined_peak_upper_bound_kib': peak + parent_peak,
            'parent_initial_exec_peak_kib': parent_initial_peak,
            'parent_raw_rusage_including_launch_history_kib': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
            'supervisor_peak_source': 'Current-exec /proc/self/status VmHWM; raw launch-history rusage retained separately',
            'source_sha256': sha(Path(__file__)), 'profile_sha256': sha(ROOT / 'archive-client-profile.json'),
            'readback_working_directory_removed': not work.exists(), 'only_owned_process_group_supervised': True}
        (ROOT / 'archive-client-measurement.json').write_text(json.dumps(report, indent=2) + '\n')
        print(json.dumps(report, indent=2))
        assert code == 0 and stopped is None and peak + parent_peak <= 500 * 1024


if __name__ == '__main__':
    main()
