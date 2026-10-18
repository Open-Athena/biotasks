"""Freeze reviewed alpha-diversity exports for no-model provider checks."""
import argparse
import hashlib
import json
from pathlib import Path
from alpha_runtime_input import check_task, REVIEWED
from package_provider_task import pack

CODE = ('alpha_runtime_input.py', 'history_runtime_input.py',
        'alpha_provider_environment.py', 'history_provider_environment.py',
        'pr_provider_environment.py', 'run_pr_provider_preflight.py',
        'run_alpha_provider_preflight.py', 'package_provider_task.py',
        'preserve_author_output.py')
EXPECTED = {
    'esty_ci': {'baseline': 0, 'native_reference': 1,
                'alternative_factored_variance': 1,
                'wrong_clipped_lower': 0, 'wrong_omit_doubletons': 0},
    'observed_features': {'equivalent_nonzero_count': 1,
                         'wrong_counts_zeros': 0, 'wrong_constant': 0},
}


def prepare(task, controls, source, output, function):
    from repo2rlenv.emitter.bundle import inspect_bundle
    identity = inspect_bundle(task)
    if not identity['integrity_passed'] or identity['bundle_hash'] not in REVIEWED:
        raise ValueError('Unreviewed or changed native bundle')
    recipe = REVIEWED[identity['bundle_hash']]
    if (function == 'esty_ci') != (recipe == 'swe_smith'):
        raise ValueError('Function and source bundle differ')
    rows = json.loads(controls.read_text())['records']
    rewards = {r['case']: r['reward'] for r in rows}
    if rewards != EXPECTED[function] or len(rows) != len(rewards):
        raise ValueError('Independent control outcomes differ')
    if not all(r['completed'] and r['passed'] and r['exception_type'] is None for r in rows):
        raise ValueError('Independent controls incomplete')
    assets = {}
    total = 0
    for path in task.rglob('*'):
        if path.is_symlink():
            raise ValueError('Linked task asset')
        if path.is_file():
            total += path.stat().st_size
            with path.open('rb') as stream:
                digest = hashlib.file_digest(stream, 'sha256').hexdigest()
            assets[path.relative_to(task).as_posix()] = {
                'sha256': digest, 'mode': path.stat().st_mode & 0o7777}
    if total > 384*1024**2:
        raise ValueError('Transfer allowance exceeded')
    output.mkdir(parents=True, exist_ok=False)
    review = {'status': 'runtime_probe_only_acceptance_pending',
              'source_bundle_hash': identity['bundle_hash'],
              'reward': {'range': [0, 1]}, 'assets': assets,
              'independent_controls': rewards,
              'control_summary_sha256': hashlib.sha256(controls.read_bytes()).hexdigest(),
              'limits': ['Native contrast previously passed; fresh provider check not executed',
                         'Final scientific acceptance and blind attempt remain pending']}
    (output/'input-review.json').write_text(json.dumps(review, indent=2)+'\n')
    check_task(task, output/'input-review.json')
    transfer = pack(task, output/'task-bundle.tar.gz')
    (output/'task-bundle-manifest.json').write_text(json.dumps(transfer, indent=2)+'\n')
    root = Path(__file__).resolve().parent
    for name in CODE:
        (output/name).write_bytes((root/name).read_bytes())
    (output/'glm_remote.py').write_bytes((root/'run_alpha_provider_remote.py').read_bytes())
    raw = source.read_bytes()
    if hashlib.sha256(raw).hexdigest() != '7e387fbb04d5374964de37a31b63e6cabc310198703213c6a40bf8d5c6dd4755':
        raise ValueError('Runtime source changed')
    (output/'repo2rlenv-source.tar.gz').write_bytes(raw)
    files = {}
    for path in sorted(output.iterdir()):
        with path.open('rb') as stream:
            files[path.name] = {'bytes': path.stat().st_size,
                               'sha256': hashlib.file_digest(stream, 'sha256').hexdigest()}
    result = {'stage': 'prepared_not_dispatched', 'function': function,
              'source_bundle_hash': identity['bundle_hash'], 'model_calls': 0,
              'required_slots': 3, 'probe_seconds': 1800, 'cleanup_seconds': 240,
              'task_uncompressed_bytes': total, 'files': files}
    (output/'manifest.json').write_text(json.dumps(result, indent=2)+'\n')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('task', 'controls', 'source', 'output'):
        parser.add_argument('--'+name, type=Path, required=True)
    parser.add_argument('--function', choices=tuple(EXPECTED), required=True)
    args = parser.parse_args()
    print(json.dumps(prepare(args.task, args.controls, args.source, args.output, args.function)))
