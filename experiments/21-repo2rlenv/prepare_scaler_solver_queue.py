"""Prepare immutable SCALER transfers; does not allocate workers or call models."""
import argparse
import hashlib
import json
from pathlib import Path

from package_provider_task import pack, unpack


def prepare(tasks, acceptance_root, output):
    output.mkdir(parents=True, exist_ok=False)
    decisions = json.loads((acceptance_root / 'summary.json').read_text())
    rows = []
    for item in decisions['tasks']:
        name = item['task']
        task = tasks / name
        acceptance = acceptance_root / (name + '.json')
        decision = json.loads(acceptance.read_text())
        assert decision['status'] == 'accepted_for_bounded_pilot'
        assert decision['reward']['range'] == [-1, 1]
        assets = {str(p.relative_to(task)): hashlib.sha256(p.read_bytes()).hexdigest()
                  for p in task.rglob('*') if p.is_file()}
        assert assets == decision['asset_sha256'], name
        target = output / name
        target.mkdir()
        manifest = pack(task, target / 'task-bundle.tar.gz')
        (target / 'task-bundle-manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
        (target / 'task-file-modes.json').write_text(json.dumps(
            {key: value['mode'] for key, value in manifest['files'].items()}, indent=2) + '\n')
        (target / 'acceptance.json').write_bytes(acceptance.read_bytes())
        unpack(target / 'task-bundle.tar.gz', target / 'task-bundle-manifest.json', target / 'roundtrip')
        recovered = target / 'roundtrip/task'
        for key, digest in assets.items():
            assert hashlib.sha256((recovered / key).read_bytes()).hexdigest() == digest
            assert (recovered / key).stat().st_mode & 0o777 == manifest['files'][key]['mode']
        rows.append({'task': name, 'task_id': decision['task_id'],
                     'archive_sha256': manifest['archive_sha256'], 'asset_count': len(assets),
                     'stage': 'transfer_prepared', 'provider_controls': 'pending',
                     'blind_attempts': 0, 'native_reward_range': [-1, 1]})
    result = {'stage': 'prepared_not_dispatched', 'tasks': rows,
              'provider': 'scaler_provider_environment:RecordedDaytonaEnvironment',
              'required_provider_controls': {'nop': -1, 'oracle': 1},
              'solver': {'attempts_per_task': 1, 'timeout_seconds': 900,
                         'max_turns': 12, 'max_output_tokens': 2048,
                         'reasoning_effort': 'unset'},
              'dispatch_requires': ['free capacity for controller and separate learner/verifier',
                                    'budget reservation', 'provider controls and cleanup verified'],
              'model_calls': 0, 'remote_allocations': 0}
    (output / 'queue.json').write_text(json.dumps(result, indent=2) + '\n')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--tasks', type=Path, required=True)
    parser.add_argument('--acceptance-root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(prepare(args.tasks, args.acceptance_root, args.output)))
