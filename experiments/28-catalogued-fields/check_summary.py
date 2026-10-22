"""Synthetic accounting checks; never rely on mutable cohort outcomes."""

from copy import deepcopy
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from summarize import summarize


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value))


with TemporaryDirectory(prefix='biotasks28-summary-check-') as directory:
    root = Path(directory)
    cohort = [{'repo': 'fixture/' + name, 'slug': name, 'field_label': name,
               'ref': name, 'window_count': 3} for name in ['good', 'failed']]
    save(root / 'cohort.json', cohort)
    initial = summarize(root)
    assert not initial['completion_proven']
    assert initial['repositories'][0]['actual_cost_usd'] is None
    assert initial['repositories'][0]['verified_tasks'] is None
    task = {'independently_verified_tracked_tests': True,
        'strict_oracle_command_resolved': False,
        'trials': {agent: {'reward': reward, 'reward_consistent': True,
            'reward_details': {'parse_status': 'ok'}, 'exception': None}
            for agent, reward in [('nop', 0), ('oracle', 1)]}}
    for row in cohort:
        name = row['slug']
        result = {'repo': row['repo'], 'ref': row['ref'],
            'task_controls': [deepcopy(task)] if name == 'good' else [],
            'task_files_unchanged': {'verified': True}, 'verified_tasks': int(name == 'good'),
            'billing': {'cost_complete': True, 'actual_cost_usd': '1.25'},
            'allocated_cpu_hours': 2, 'artifact_readback_verified': True,
            'owned_cleanup_verified_empty': True, 'furthest_stage_reached': 'fixture',
            'native_status': 'fixture', 'native_candidates_returned': None,
            'candidates_entered': 0, 'paired_validation_started': 0,
            'paired_validation_completed': 0, 'native_skip_reasons': {},
            'native_exports': int(name == 'good'), 'control_allocation_rows': [],
            'failure_cause': 'fixture'}
        save(root / 'results' / (name + '.json'), result)
        manifest = root / 'archives' / (name + '-manifest.json')
        save(manifest, {'fixture': name})
        save(root / 'archives' / (name + '-receipt.json'), {
            'anonymous_download_verified': True,
            'manifest_sha256': hashlib.sha256(manifest.read_bytes()).hexdigest()})
    complete = summarize(root)
    assert complete['completion_proven']
    assert complete['known_reported_actual_cost_usd'] == '2.50'
    assert complete['cost_per_verified_task_usd'] == '2.50'  # Includes failed repo.
    assert complete['cost_per_successful_repository_usd'] == '2.50'
    assert complete['repositories'][0]['strict_verified_oracle_command_resolved_tasks'] == 0
    receipt = root / 'archives/failed-receipt.json'
    receipt.unlink()
    partial = summarize(root)
    assert not partial['completion_proven'] and partial['cost_per_verified_task_usd'] is None
    assert partial['verified_tasks_with_archived_evidence'] == 1
    path = root / 'results/good.json'
    result = json.loads(path.read_text())
    result['billing']['cost_complete'] = False
    save(path, result)
    unknown = summarize(root)
    assert unknown['repositories'][0]['actual_cost_usd'] is None
    assert unknown['verified_tasks_with_archived_evidence'] == 0
    result['billing']['cost_complete'] = True
    result['task_controls'][0]['trials']['oracle']['exception'] = 'VerifierTimeoutError'
    save(path, result)
    try:
        summarize(root)
    except AssertionError:
        pass
    else:
        raise AssertionError('Contradictory claimed verification was accepted')

print('Summary accounting checks passed: absent/unknown != zero, failed-repo costs included, '
      'full evidence required for ratios, timeout cannot retain claimed verification.')
