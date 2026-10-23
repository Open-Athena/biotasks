"""Bounded archive readback of the frozen replay, without raw public log uploads."""
import hashlib
import json
from pathlib import Path, PurePosixPath
import subprocess
import tarfile
import zstandard

ROOT = Path(__file__).resolve().parent

def sha(path):
    with path.open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def main():
    account = json.loads((ROOT / 'macs-742-image-accounting.json').read_text())
    assert account['state'] in ('failed', 'succeeded') and account['attempts'] == 1
    a = account['output_archive']
    assert a['state'] == 'uploaded' and a['size_bytes'] < 16 * 1024**2
    dest = ROOT / 'inputs-private/macs-742-image-001'
    dest.mkdir(mode=0o700, exist_ok=True)
    archive = dest / 'outputs.tar.zst'
    if not archive.exists():
        subprocess.run(['/home/exedev/.local/google-cloud-sdk/bin/gcloud', 'storage', 'cp', '--quiet', a['uri'], str(archive)], capture_output=True, check=True, timeout=90)
    assert archive.stat().st_size == a['size_bytes'] and sha(archive) == a['sha256']
    members = []
    total = 0
    seen = set()
    with archive.open('rb') as raw, zstandard.ZstdDecompressor().stream_reader(raw) as stream, tarfile.open(fileobj=stream, mode='r|') as tar:
        for member in tar:
            path = PurePosixPath(member.name)
            assert not path.is_absolute() and '..' not in path.parts
            if member.isdir():
                continue
            assert member.isfile() and member.size < 16 * 1024**2
            assert member.name not in seen
            seen.add(member.name)
            total += member.size
            assert total < 64 * 1024**2
            target = dest / member.name
            target.parent.mkdir(parents=True, exist_ok=True)
            data = tar.extractfile(member).read()
            if target.exists():
                assert target.read_bytes() == data
            else:
                target.write_bytes(data)
                target.chmod(0o600)
            members.append({'path': member.name, 'bytes': len(data), 'sha256': sha(target)})
    report = json.loads((dest / 'macs-longcheck-result.json').read_text())
    assert report['run_id'] == 'biotasks34-macs-742-image-001' and report['model_calls'] == 0
    assert report['payload_sha256'] == 'bae10d85d1f89b111de6df621fe02a2f4226f17eb62ba80fcdc7d87760ed3e5a'
    result_path = ROOT / 'macs-742-image-result-001.json'
    if result_path.exists():
        assert json.loads(result_path.read_text()) == report
    result_path.write_text(json.dumps(report, indent=2) + '\n')
    replay = report.get('replay')
    if replay:
        assert replay == json.loads((dest / 'actions/replay.json').read_text())
        original = json.loads((ROOT / 'inputs-private/macs-recorded-replay.json').read_text())
        for row, action in zip(replay['steps'], original['actions'], strict=False):
            assert all(row[key] == action[key] for key in ('step', 'command_sha256', 'expected_exit_code', 'timeout_seconds'))
            for stream_name in ('stdout', 'stderr'):
                key = stream_name + '_sha256'
                if key in row:
                    assert sha(dest / f"actions/step-{row['step']:03d}-{stream_name}.txt") == row[key]
    calls = dest / 'docker-calls.jsonl'
    if calls.exists():
        for line in calls.read_text().splitlines():
            row = json.loads(line)
            for stream_name in ('stdout', 'stderr'):
                assert sha(dest / f"call-{row['sequence']:03d}-{stream_name}.txt") == row[stream_name + '_sha256']
    receipt = {'archive_sha256': a['sha256'], 'members': members, 'state': account['state'],
               'result_record_verified': True, 'replay_status': replay['status'] if replay else None,
               'steps_attempted': len(replay['steps']) if replay else 0,
               'retained_image_id': report.get('retained_image_id'),
               'cleanup_verified': report.get('cleanup_verified', False),
               'owned_containers_absent': report.get('owned_containers_absent', False),
               'context_tools_removed': report.get('context_tools_removed', False),
               'model_calls': 0, 'controls_run': 0, 'allocated_cpu_hours': account['allocated_cpu_hours']}
    (ROOT / 'macs-742-image-readback-001.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps({k: v for k, v in receipt.items() if k != 'members'}))

if __name__ == '__main__':
    main()
