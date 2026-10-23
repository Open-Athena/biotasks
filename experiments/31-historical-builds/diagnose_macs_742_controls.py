"""Extract a bounded, deterministic failure summary from verified private controls."""
import hashlib
import json
from pathlib import Path
import tarfile

ROOT = Path(__file__).resolve().parent
ARCHIVE = ROOT / 'inputs-private/macs-742-controls-001/control-artifacts.tar.gz'


def main():
    account = json.loads((ROOT / 'macs-742-controls-accounting.json').read_text())
    controls = json.loads((ROOT / 'macs-742-control-results.json').read_text())
    members = {row['path']: row for row in controls['archive_members']}
    assert controls['archive_sha256'] == account['output_archive']['sha256']
    row = members['control-artifacts.tar.gz']
    assert ARCHIVE.stat().st_size == row['bytes']
    with ARCHIVE.open('rb') as stream:
        assert hashlib.file_digest(stream, 'sha256').hexdigest() == row['sha256']
    assert controls['task_files_unchanged'] and controls['verified_task_files'] == 10
    assert {r['agent'] for r in controls['rows']} == {'nop', 'oracle'}
    observations = []
    with tarfile.open(ARCHIVE) as tar:
        for member in tar:
            if not member.name.endswith('/verifier/test-stdout.txt'):
                continue
            agent = 'oracle' if '-oracle/' in member.name else 'nop' if '-nop/' in member.name else None
            assert agent and member.isfile() and member.size < 128 * 1024
            raw = tar.extractfile(member).read()
            output = raw.decode('utf-8', errors='replace')
            assert 'R2E_REBUILD_FAILED' in output
            assert 'Installing build dependencies: finished with status' in output
            assert 'setuptools>=80.0' in output
            assert 'Connection refused' in output
            observations.append({
                'agent': agent,
                'stdout_sha256': hashlib.sha256(raw).hexdigest(),
                'stdout_bytes': len(raw),
                'connection_refused_count': output.count('Connection refused'),
                'rebuild_failed_marker': True,
                'missing_build_requirement': 'setuptools>=80.0',
                'failure_phase': 'pip isolated build dependency download during recorded editable install',
            })
    assert {r['agent'] for r in observations} == {'nop', 'oracle'}
    for trial in controls['rows']:
        assert trial['state'] == 'completed' and trial['reward'] == 0
        assert trial['parse_status'] == 'rebuild_incomplete' and trial['test_exit_code'] is None
    result = {
        'scope': 'Post hoc diagnosis of one immutable PR742 candidate Harbor control pair',
        'archive_sha256': controls['archive_sha256'],
        'task_files_unchanged': True,
        'verified_task_files': 10,
        'observations': sorted(observations, key=lambda r: r['agent']),
        'positive_control_pair': False,
        'failure_class': 'rebuild dependency fetch failure in the Harbor verifier runtime',
        'attribution_limit': 'Connection refused identifies a failed package-index connection; the archive does not distinguish egress policy, index configuration, or transient service failure.',
        'test_execution': 'F2P and P2P tests were not reached in either control',
        'model_calls': 0,
        'task_repairs': 0,
    }
    (ROOT / 'macs-742-control-diagnosis.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: v for k, v in result.items() if k != 'observations'}))


if __name__ == '__main__':
    main()
