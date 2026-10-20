"""Join preserved first-pass and continuation admissions without merging rewards."""
import csv
from collections import Counter
import datetime
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent


def build():
    sources = {}

    def read(path):
        file = ROOT / path
        raw = file.read_bytes()
        sources[path] = hashlib.sha256(raw).hexdigest()
        return json.loads(raw)

    census = read('evidence/campaign-census-20261018/census.json')
    for path, expected in census['source_sha256'].items():
        raw = (ROOT / path).read_bytes()
        assert hashlib.sha256(raw).hexdigest() == expected, path
    tracker = read('continuation-20261018/target-tracker.json')
    newer = read('continuation-20261018/new-admissions.json')
    budget = read('continuation-20261018/budget.json')
    tasks = []
    scaler = read('evidence/scaler-native-acceptance/summary.json')['tasks']
    for unit in census['units']:
        for admission in unit['current_admissions']:
            identity = admission.get('task_id', admission.get('task'))
            accepted = read(admission['source'])
            if unit['route'] == 'reasoning_synth/scaler':
                task = next(x['task'] for x in scaler if x['task_id'] == identity)
                matches = [r for r in unit['blind_results'] if read(r['source']).get('task') == task]
            elif unit['route'] == 'pr_diff/native':
                task = admission['task']
                matches = [r for r in unit['blind_results'] if r['task'] == task]
            else:
                task = accepted.get('task', identity)
                matches = unit['blind_results']
            assert len(matches) == 1
            result = matches[0]
            evidence = read(result['source'])
            if unit['route'] == 'pr_diff/native':
                actual = next(x for x in evidence['tasks'] if x['task'] == task)
                reward = actual['native_similarity_reward']
                assert reward == result['native_similarity_reward']
                assert actual['task_checksum'] == admission['runtime_checksum']
            else:
                actual = evidence
                reward = evidence['reward']
                assert reward == result['reward']
            assert actual['attempts'] == 1
            assert not actual.get('exception_type') and not actual.get('exception') and not actual.get('trial_exception')
            tasks.append({'unit_id': unit['unit_id'], 'route': unit['route'],
                          'repository': unit['repository'], 'cohort': unit['cohort'],
                          'task_id': identity, 'native_task': task, 'phase': 'first_pass',
                          'reward_semantics': admission['reward_semantics'],
                          'blind_attempts': 1, 'native_reward': reward,
                          'solver_state': 'scored', 'admission_source': admission['source'],
                          'solver_source': result['source']})
    for key, admissions in newer.items():
        for row in admissions:
            task = {'unit_id': key, 'route': row['route'], 'repository': row['repository'],
                    'cohort': None, 'task_id': row['task_id'], 'native_task': row['task_id'],
                    'phase': 'continuation', 'reward_semantics': row['reward_semantics'],
                    'blind_attempts': row['blind_solver_attempts'],
                    'native_reward': row.get('blind_native_reward'),
                    'solver_state': ('scored' if 'blind_native_reward' in row else
                                     'active_counter_unobserved' if row['blind_solver_attempts'] is None else
                                     'attempted_unscored' if row['blind_solver_attempts'] else 'pending'),
                    'admission_source': 'continuation-20261018/new-admissions.json',
                    'solver_source': row.get('blind_audit_source'),
                    'admission_artifact_prefix': row['artifact_prefix'],
                    'solver_artifact_prefix': row.get('blind_artifact_prefix')}
            assert task['blind_attempts'] in (None, 0, 1)
            if task['blind_attempts'] is None:
                assert row.get('active_blind_job_id') and task['native_reward'] is None
            if task['native_reward'] is not None:
                assert task['blind_attempts'] == 1
                # Earlier reports use both experiment-relative and
                # continuation-relative paths. Canonicalize and read the
                # actual independent score evidence rather than trusting a
                # copied scalar in the living admission record.
                source = task['solver_source']
                assert source, 'Scored continuation task requires audit evidence'
                candidates = {(base / source).resolve() for base in (ROOT, HERE)
                              if (base / source).is_file()}
                assert len(candidates) == 1, source
                task['solver_source'] = str(candidates.pop().relative_to(ROOT))
                audit = read(task['solver_source'])
                matches = [item for item in audit.get('records', [audit])
                           if item['task_id'] == task['task_id']]
                assert len(matches) == 1
                proof = matches[0]
                actual_reward = (proof['blind_grade']['reward'] if 'blind_grade' in proof
                                 else proof['blind_reward'])
                assert proof['blind_attempts'] == 1 and actual_reward == task['native_reward']
                assert proof['admitted_asset_manifest_sha256'] == row['portable_asset_manifest_sha256']
                if 'blind_task_checksum' in row:
                    assert proof['task_checksum'] == row['blind_task_checksum']
                task['blind_task_checksum'] = proof['task_checksum']
            tasks.append(task)
    assert len({(x['unit_id'], x['task_id']) for x in tasks}) == len(tasks)
    provenance = read('continuation-20261018/accepted-instance-provenance-summary.json')
    matched_provenance = set()
    for task in tasks:
        matches = [(index, row) for index, row in enumerate(provenance['rows'])
                   if row['route'] == task['route']
                   and row['task_id'] in (task['task_id'], task['native_task'])]
        assert len(matches) == 1, (task['route'], task['task_id'])
        index, record = matches[0]
        assert index not in matched_provenance
        matched_provenance.add(index)
        task['provenance_category'] = record['category']
        task['unchanged_output_evidence_eligible'] = record['category'] in {
            'authored_output_unchanged',
            'programmatic_output_unchanged_from_supplied_family',
        }
    assert len(matched_provenance) == len(provenance['rows'])
    provenance_counts = dict(Counter(task['provenance_category'] for task in tasks))
    assert provenance_counts == provenance['categories']
    for unit in tracker['rows']:
        assert unit['total_admitted'] == sum(t['unit_id'] == unit['unit_id'] for t in tasks)
    groups = {}
    for name, selected in [('patch_similarity', [t for t in tasks if t['route'] == 'pr_diff/native']),
                           ('correctness_and_algorithmic', [t for t in tasks if t['route'] != 'pr_diff/native'])]:
        scored = [t for t in selected if t['native_reward'] is not None]
        groups[name] = {'admitted': len(selected), 'scored': len(scored),
                        'maximum_reward': sum(t['native_reward'] == 1 for t in scored),
                        'partial_reward': sum(0 < t['native_reward'] < 1 for t in scored),
                        'zero_reward': sum(t['native_reward'] == 0 for t in scored),
                        'pending': len(selected) - len(scored)}
    # Failed pre-execution launch rows retain their original hold description.
    # The explicit transfer points at the replacement row; count it only there.
    runs = {row['run']: row for row in budget['runs']}
    transferred = [row for row in budget['runs'] if row.get('hold_transferred_to')]
    for row in transferred:
        target = row['hold_transferred_to']
        assert target != row['run'] and target in runs
        assert runs[target]['daytona_hold_usd'] >= row['daytona_hold_usd']
    effective_holds = sum(row['daytona_hold_usd'] for row in budget['runs']
                          if not row.get('hold_transferred_to'))
    assert budget['accounted_estimates_and_holds_usd'] == budget['historical_first_pass_estimates_and_holds_usd'] + effective_holds
    assert budget['remaining_conservative_allowance_usd'] == budget['ceiling_usd'] - budget['accounted_estimates_and_holds_usd']
    return {'as_of_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'stage': 'consolidated_verified_results_so_far_not_final_completion',
            'tasks': tasks, 'units': tracker['rows'], 'reward_groups': groups,
            'automatic_output_accounting': {
                'categories': provenance_counts,
                'unchanged_accepted_outputs': sum(task['unchanged_output_evidence_eligible'] for task in tasks),
                'unattended_end_to_end_yield_established': False,
                'interpretation': 'Accepted instances and blind scores below include legacy assisted evidence. Unchanged authored outputs and unchanged programmatic instances from the declared supplied family support separate parts of the output comparison. The supplied Scaler family was human-authored; instance expansion does not establish family invention. Curated setup, manual orchestration and final assessment remain disclosed; these counts are not production acceptance rates.'},
            'total_admitted': len(tasks), 'total_scored': sum(t['native_reward'] is not None for t in tasks),
            'budget': {k: budget[k] for k in ['ceiling_usd', 'historical_first_pass_estimates_and_holds_usd', 'continuation_estimates_and_holds_usd', 'accounted_estimates_and_holds_usd', 'remaining_conservative_allowance_usd', 'provider_invoice_verified', 'credit_balance_verified']},
            'budget_hold_accounting': {'explicit_transfer_rows': [row['run'] for row in transferred],
                                      'transferred_holds_excluded_usd': sum(row['daytona_hold_usd'] for row in transferred),
                                      'effective_continuation_holds_usd': effective_holds},
            'source_sha256': sources,
            'limitations': ['No common pass-rate aggregation across unlike reward semantics.',
                           'Related PR/commit/mutation variants can share source families; task instances are not independent competencies.',
                           'Historical capture gaps and unreconciled counters stay unknown.',
                           'Reservations and historical estimates are not actual billed cost.',
                           'Independent acceptance includes manual review and recorded interventions; it does not prove unattended GLM-only production.']}


def markdown(data):
    lines = ['## Consolidated result ledger', '',
             'First pass and continuation combined, including legacy assisted evidence. Acceptance below includes allowed final Codex assessment; it does not mean an unchanged automatic output. A scored attempt is separate from acceptance. Pending outcomes are not zero scores.', '',
             '### Automatic-output provenance', '',
             'The comparison assesses the automatic pipeline. Task-specific repairs and feedback cannot contribute primary successes. Unchanged accepted outputs still do not establish unattended setup, orchestration or production yield.', '',
             '| Accepted-instance provenance | Instances |', '| --- | ---: |']
    for category, count in data['automatic_output_accounting']['categories'].items():
        lines.append(f"| {category.replace('_', ' ')} | {count} |")
    lines += ['', '### Native reward results for all accepted evidence', '',
             '| Reward family | Accepted | Scored once | Maximum reward | Partial | Zero | Pending |',
             '| --- | ---: | ---: | ---: | ---: | ---: | ---: |']
    for label, key in [('Correctness / algorithmic', 'correctness_and_algorithmic'), ('Patch similarity', 'patch_similarity')]:
        g = data['reward_groups'][key]
        lines.append('| ' + label + ' | ' + ' | '.join(str(g[k]) for k in ['admitted', 'scored', 'maximum_reward', 'partial_reward', 'zero_reward', 'pending']) + ' |')
    lines += ['', '### Repository-route ledger', '',
              'Cells are **accepted tasks / charged candidate attempts**. The target is 3 accepted tasks per supported cell, with a cap of 10 candidates. `?` means the counter is not reconciled; `—` means unsupported native language/profile; `B` marks a model/backend/input blocker. Candidate definitions differ by recipe, so these are tracking counts rather than comparable production-yield estimates.', '',
              '| Route | Biopython | scikit-bio | bedtools2 | DESeq2 |', '| --- | ---: | ---: | ---: | ---: |']
    repos = ['biopython/biopython', 'scikit-bio/scikit-bio', 'arq5x/bedtools2', 'thelovelab/DESeq2']
    for route in dict.fromkeys(r['route'] for r in data['units'] if r['repository']):
        cells = []
        for repo in repos:
            r = next(r for r in data['units'] if r['route'] == route and r['repository'] == repo)
            cell = '—' if r['target'] is None else str(r['total_admitted']) + ' / ' + ('?' if r['charged_candidate_attempts'] is None else str(r['charged_candidate_attempts']))
            if r['state'].startswith('blocked_'): cell += ' B'
            cells.append(cell)
        lines.append('| ' + route + ' | ' + ' | '.join(cells) + ' |')
    lines += ['', '### Seed-cohort ledger', '', '| Recipe / fixed cohort | Accepted | Charged candidates | State |', '| --- | ---: | ---: | --- |']
    for r in data['units']:
        if r['repository'] is None:
            count = '?' if r['charged_candidate_attempts'] is None else str(r['charged_candidate_attempts'])
            lines.append(f"| {r['route']} / {r['input_cohort']} | {r['total_admitted']}/3 | {count}/10 | {r['state'].replace('_', ' ')} |")
    lines += ['', '### Accepted-task score ledger', '', '| Route | Repository / cohort | Task | Single-attempt GLM native reward |', '| --- | --- | --- | ---: |']
    aliases = {'repo2rlenv-pr-runtime/818edf065df952df43f80f897de021e3ce9bc91c2957298060cddedd72487140': 'PR2633',
               'repo2rlenv-swe-smith/8ab8eb1ddfed62315e8f8f0e04330836098aec80b7500ccc1437b717321f2511': 'LCC constant mutation'}
    for t in data['tasks']:
        name = aliases.get(t['native_task'], t['native_task'])
        reward = 'pending' if t['native_reward'] is None else f"{t['native_reward']:g}"
        lines.append(f"| {t['route']} | {t['repository'] or t['cohort']} | {name} | {reward} |")
    lines += ['', 'Patch-similarity rewards do not establish functional correctness. Scaler uses native −1/+1 rewards; the other scored correctness profiles use 0–1. No combined benchmark pass rate is claimed. Full stable identities and source hashes are preserved in `consolidated-ledger.json`.']
    return '\n'.join(lines) + '\n'


if __name__ == '__main__':
    data = build()
    (HERE / 'consolidated-ledger.json').write_text(json.dumps(data, indent=2) + '\n')
    (HERE / 'consolidated-ledger.md').write_text(markdown(data))
    with (HERE / 'consolidated-task-ledger.csv').open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(dict.fromkeys(k for t in data['tasks'] for k in t)), lineterminator='\n')
        writer.writeheader()
        writer.writerows(data['tasks'])
    print(json.dumps({'accepted': data['total_admitted'], 'scored': data['total_scored'], 'groups': data['reward_groups']}))
