"""Bounded integrity/completion audit; never execute native tasks or models."""
import hashlib
import importlib.metadata
import io
import json
from pathlib import Path
import tarfile

import zstandard

ROOT = Path(__file__).resolve().parent
EV = ROOT / 'evidence'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def main():
    receipt = json.loads((EV / 'archive-readback.json').read_text())
    original = (EV / 'outputs.tar.zst').read_bytes()
    assert len(original) == receipt['size_bytes']
    assert digest(original) == receipt['archive_sha256']
    assert len(original) < 1024**2
    verified = []
    with zstandard.ZstdDecompressor().stream_reader(io.BytesIO(original)) as stream:
        with tarfile.open(fileobj=stream, mode='r|') as bundle:
            total = 0
            for member in bundle:
                assert member.isdir() or member.isfile()
                if member.isdir():
                    continue
                assert Path(member.name).name == member.name
                total += member.size
                assert total < 10 * 1024**2
                name = Path(member.name)
                target = EV / (name.stem + '.txt' if name.suffix == '.log' else name.name)
                assert bundle.extractfile(member).read() == target.read_bytes(), member.name
                verified.append(member.name)
    with tarfile.open(EV / 'native-artifacts.tar.gz') as bundle:
        total = 0
        for member in bundle:
            path = Path(member.name)
            assert not path.is_absolute() and '..' not in path.parts
            assert path.parts[0] in {'bootstrap', 'outputs'}
            assert member.isdir() or member.isfile()
            total += member.size
            assert total < 10 * 1024**2
            if member.isfile():
                assert bundle.extractfile(member).read() == (EV / 'native' / path).read_bytes()
    outcomes = json.loads((EV / 'final-outcomes.json').read_text())
    lifecycle = json.loads((EV / 'lifecycle.json').read_text())
    cleanup = json.loads((EV / 'supervisor-result.json').read_text())
    assert len(lifecycle['runs']) == 5 and lifecycle['all_terminal']
    assert lifecycle['total_allocated_cpu_hours'] < 48
    assert not json.loads((EV / 'exported-tasks.json').read_text())
    assert not list((EV / 'native/outputs').rglob('task.toml'))
    assert all(not cleanup[k] for k in ['remaining_containers', 'remaining_controllers', 'remaining_images'])
    assert outcomes['counts']['agent_iterations'] <= 60
    assert all(row['agent_iterations'] <= 20 for row in outcomes['repositories'])
    assert sum(r['comparison_input'] for r in outcomes['cases']) == 5
    assert len(outcomes['cases']) == 16
    for path in (ROOT / 'proposed-configs').glob('*.json'):
        config = json.loads(path.read_text())
        assert config['bootstrap']['max_iterations'] == 20
        assert config['bootstrap']['max_llm_spend_usd'] == 5
        assert config['llm']['provider'] == 'openrouter'
        assert config['llm']['model'] == 'z-ai/glm-5.3'
        assert config['llm']['fallback'] is None
        assert config['auth']['use_gh_cli'] is False
    members = []
    for folder in [EV, ROOT / 'licenses']:
        for path in sorted(folder.rglob('*')):
            if path.is_file():
                raw = path.read_bytes()
                members.append({'path': str(path.relative_to(ROOT)), 'size_bytes': len(raw), 'sha256': digest(raw)})
    manifest = {'retention': 'Permanent research branch; retain while cited. No automatic expiry.',
                'upstream_revision': '27d04ee8203cd5b2f20c3997d13836e5f5b64238',
                'native_input_checkpoint': '8c67bf99', 'files': members}
    (ROOT / 'artifact-manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    result = {'archive_checksum_verified': True, 'original_members_match_retained_files': verified,
              'nested_archive_members_match': True, 'source_files_modified': False,
              'source_verification_basis': 'Pinned archive checksum checked during installation; no source patch or monkeypatch applied.',
              'all_jobs_terminal': True, 'owned_cleanup_verified': True, 'exports': 0,
              'grading_requirement': 'No exported tasks; no grading input exists.',
              'input_and_iteration_bounds_verified': True, 'billed_cost_verifiable': False,
              'artifact_manifest_sha256': digest((ROOT / 'artifact-manifest.json').read_bytes()),
              'zstandard_version': importlib.metadata.version('zstandard'),
              'remote_git_readback': 'pending'}
    (ROOT / 'verification.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
