"""Bound retained solver-batch sandbox costs without inventing lifecycle timestamps."""
import hashlib
import json
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
BATCHES = (
    ('history-five-blind-02', 'history-five-blind-20261019-02'),
    ('authored-two-blind-03', 'authored-two-blind-20261019-03'),
    ('authored-tsallis-blind-03', 'authored-tsallis-blind-20261019-03'),
)
RATE = 2 * .0504 + 4 * .0162 + 10 * .000108


def build():
    sources = {}

    def read(name):
        raw = (HERE / name).read_bytes()
        sources[name] = hashlib.sha256(raw).hexdigest()
        return json.loads(raw)

    tasks = read('consolidated-ledger.json')['tasks']
    known_lifetimes = {r['worker_id'] for r in read('worker-cost-evidence-inventory.json')['workers']}
    seen = set()
    rows = []
    for label, cohort in BATCHES:
        submission = read(cohort + '-submission.json')
        observation = read(cohort + '-observation.json')
        assert observation['state'] == 'SUCCEEDED'
        audit = read(label + '/independent-audit.json')
        clean = {r['sandbox_id']: r for r in read(label + '/cleanup-verification.json')}
        start = datetime.fromisoformat(submission['submitted_utc'])
        assert observation['job_id'] == submission['job_id']
        for record in audit['records']:
            matches = [t for t in tasks if t['task_id'] == record['task_id']
                       and (t.get('solver_source') or '').endswith(label + '/independent-audit.json')]
            assert len(matches) == 1, 'Task identities can overlap routes; require exact solver provenance'
            task = matches[0]
            assert record['blind_attempts'] == 1
            ids = record['exact_owned_sandbox_ids']
            assert not (set(ids) & seen)
            assert not (set(ids) & known_lifetimes), 'Do not double count measured workers'
            seen.update(ids)
            bounds = []
            for wid in ids:
                deletion = clean[wid]
                assert deletion['confirmed_absent'] and deletion['lookup_http_status'] == 404
                end = datetime.fromisoformat(deletion['observed_utc'])
                seconds = (end - start).total_seconds()
                assert seconds > 0
                bounds.append({'sandbox_id': wid, 'allocation_not_before_utc': start.isoformat(),
                               'independently_absent_at_utc': end.isoformat(),
                               'sandbox_hours_upper_bound': seconds / 3600})
            hours = sum(r['sandbox_hours_upper_bound'] for r in bounds)
            rows.append({'task_id': task['task_id'], 'route': task['route'], 'batch': cohort,
                         'phase': 'native_provider_baseline_reference_and_single_blind_attempt',
                         'sandbox_lifecycle_upper_bounds': bounds,
                         'sandbox_hours_upper_bound': hours,
                         'list_rate_compute_usd_upper_bound': hours * RATE})
    routes = []
    for route in sorted({r['route'] for r in rows}):
        selected = [r for r in rows if r['route'] == route]
        total = sum(r['list_rate_compute_usd_upper_bound'] for r in selected)
        routes.append({'route': route, 'covered_tasks': len(selected),
                       'list_rate_compute_usd_upper_bound': total,
                       'mean_upper_bound_usd_per_covered_task': total / len(selected)})
    return {'stage': 'conservative_solver_batch_bounds_not_measured_lifetimes_or_full_cost',
            'method': 'For each exact owned sandbox, bound its lifetime by job submission to independently observed deletion. All allocations originate inside the submitted job. Count the full window even when creation was later or deletion earlier.',
            'sandbox_resources': {'vcpus': 2, 'ram_gib': 4, 'disk_gib': 10},
            'resource_configuration_source': 'run_continuation_blind_trial.py:config',
            'resource_configuration_sha256': hashlib.sha256((HERE / 'run_continuation_blind_trial.py').read_bytes()).hexdigest(),
            'list_rate_usd_per_sandbox_hour': RATE,
            'rate_source': 'https://www.daytona.io/pricing', 'rate_checked_date': '2026-10-19',
            'covered_tasks': len(rows), 'unique_sandboxes': len(seen), 'rows': rows,
            'routes': routes, 'source_sha256': sources,
            'limitations': ['Upper bounds are intentionally loose; do not present as measured cost or charges.',
                           'Includes provider baseline/reference controls as well as blind solver work.',
                           'Only three retained continuation batches; no full-campaign coverage claim.',
                           'Excludes provider build/cache billing outside sandbox lifetimes, external storage and labor.',
                           'No invoice or credit verification. Existing GLM/TRC/CoreWeave incremental service charge is zero under the approved arrangement.',
                           'Do not add these upper bounds to partial lifecycle subtotals and label the sum a production price.']}


if __name__ == '__main__':
    result = build()
    (HERE / 'solver-compute-upper-bounds.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: result[k] for k in ['covered_tasks', 'unique_sandboxes', 'routes']}))
