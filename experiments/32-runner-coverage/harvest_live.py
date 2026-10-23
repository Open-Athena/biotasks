"""Verified private archive readback; summarize native outcomes without regrading."""
import hashlib
import json
from pathlib import Path, PurePosixPath
import subprocess
import tarfile
import zstandard

ROOT = Path(__file__).resolve().parent


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    account = json.loads((ROOT/'live-accounting.json').read_text())
    assert account['state'] in ('succeeded', 'failed') and account['attempts'] == 1
    a = account['output_archive']
    assert a['state'] == 'uploaded' and a['size_bytes'] < 20*1024**2
    dest = ROOT/'inputs-private/live-001'
    dest.mkdir(exist_ok=True, mode=0o700)
    archive = dest/'outputs.tar.zst'
    if not archive.exists():
        subprocess.run(['/home/exedev/.local/google-cloud-sdk/bin/gcloud', 'storage',
                        'cp', '--quiet', a['uri'], str(archive)],
                       capture_output=True, check=True, timeout=120)
    assert archive.stat().st_size == a['size_bytes'] and sha(archive) == a['sha256']
    members, total = [], 0
    with archive.open('rb') as raw, zstandard.ZstdDecompressor().stream_reader(raw) as stream, tarfile.open(fileobj=stream, mode='r|') as tar:
        for member in tar:
            path = PurePosixPath(member.name)
            assert not path.is_absolute() and '..' not in path.parts
            if member.isdir():
                continue
            assert member.isfile()
            total += member.size
            assert member.size < 20*1024**2 and total < 100*1024**2
            target = dest/member.name
            target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            data = tar.extractfile(member).read()
            assert len(data) == member.size
            if target.exists():
                assert target.read_bytes() == data
            else:
                target.write_bytes(data)
                target.chmod(0o600)
            members.append({'path': member.name, 'bytes': len(data), 'sha256': sha(target)})
    supervisor = json.loads((dest/'live-supervisor-result.json').read_text())
    summary = {'scope': 'Native target-selection comparison on reconstructed saved recipe, not exported Harbor controls',
               'job_id': account['job_id'], 'state': account['state'],
               'archive_sha256': a['sha256'], 'archive_members': members,
               'supervisor': supervisor, 'model_calls': 0,
               'allocated_cpu_hours': account['allocated_cpu_hours'], 'arms': [],
               'limits': ['Reconstructed image may differ from deleted original due to dependency drift',
                          'Pinned-ref reconstructed scripts are not retained original failed script bytes',
                          'No task exports, independent Harbor controls or model calls',
                          'Raw Matchms evidence retained privately; remote archive expires after seven days']}
    path = dest/'comparison/comparison.json'
    if path.exists():
        comparison = json.loads(path.read_text())
        assert comparison['image_id'] == supervisor['image_id']
        for arm in comparison['arms']:
            out = dest/'comparison'/f"{arm['pr']}-{arm['selection']}"
            assert json.loads((out/'calls.json').read_text()) == arm['calls']
            for call in arm['calls']:
                for stream in ('stdout', 'stderr'):
                    if stream+'_sha256' in call:
                        p = out/f"call-{call['index']:02d}-{stream}.txt"
                        assert p.stat().st_size == call[stream+'_bytes']
                        assert sha(p) == call[stream+'_sha256']
            row = {k: v for k, v in arm.items() if k != 'calls'}
            row['stages'] = [call for call in arm['calls'] if call['stage'] is not None]
            outcome_path = out/'outcome-private.json'
            if outcome_path.exists():
                outcome = json.loads(outcome_path.read_text())
                assert outcome['status'] == row['status']
                assert len(outcome['fail_to_pass']) == row['f2p_count']
                assert len(outcome['pass_to_pass']) == row['p2p_count']
                row['outcome_sha256'] = sha(outcome_path)
            summary['arms'].append(row)
        summary['comparison_containers_absent'] = comparison.get('owned_containers_absent', False)
    summary['cleanup_verified'] = bool(supervisor.get('owned_containers_absent') and
        supervisor.get('owned_image_ids_remaining') == [] and supervisor.get('local_context_tools_removed'))
    (ROOT/'live-readback.json').write_text(json.dumps(summary, indent=2)+'\n')
    print(json.dumps({'state': summary['state'], 'cleanup_verified': summary['cleanup_verified'],
                     'allocated_cpu_hours': summary['allocated_cpu_hours'],
                     'arms': [{k:v for k,v in row.items() if k not in ('stages',)} for row in summary['arms']]}))


if __name__ == '__main__':
    main()
