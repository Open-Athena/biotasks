"""Price only recorded continuation sandbox lifetimes; never infer billed totals."""
import datetime
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RATE = 2 * 0.0504 + 4 * 0.0162 + 10 * 0.000108
GROUPS = {
    'pr_runtime/native': (5, ['skbio-pr-runtime-native-01/controller-small-summary.json', 'biopython-pr-runtime-native-01/controller-small-summary.json', 'skbio-pr-numba-native-01/controller-small-summary.json', 'biopython-pr-saved-native-01/controller-small-summary.json', 'pr-correctness-controls-01/controller-small-summary.json', 'pr-correctness-controls-02/controller-small-summary.json']),
    'repo_mutate/swe_smith': (1, ['skbio-contrast-01/worker-lifecycle-projection.json', 'biopython-contrast-01/contrast-summary.json', 'robbins-controls-01/controller-small-summary.json', 'robbins-controls-02/controller-small-summary.json', 'robbins-controls-03/controller-small-summary.json', 'authored-biopython-lcc-native-01/controller-small-summary.json', 'authored-biopython-lcc-native-02/controller-small-summary.json']),
    'repo_reconstruct/swe_flow': (1, ['skbio-flow-contrast-01/contrast-summary.json', 'biopython-flow-contrast-01/contrast-summary.json', 'authored-skbio-enspie-native-01/controller-small-summary.json']),
    'commit_runtime/native': (1, ['skbio-case-commit-native-01/controller-small-summary.json', 'skbio-case-commit-native-02/controller-small-summary.json', 'commit-correctness-controls-01/controller-small-summary.json']),
}


def build():
    rows = []
    seen = set()
    for route, (accepted, paths) in GROUPS.items():
        workers = []
        for path in paths:
            raw = (ROOT / path).read_bytes()
            source = json.loads(raw)
            assert source['workers']
            for worker in source['workers']:
                identity = worker['worker_id']
                assert identity not in seen
                seen.add(identity)
                assert worker['state'] == 'terminated'
                seconds = (datetime.datetime.fromisoformat(worker['stopped_at']) - datetime.datetime.fromisoformat(worker['started_at'])).total_seconds()
                assert seconds > 0
                workers.append({'sandbox_id': identity, 'lifetime_seconds': seconds,
                                'source': path, 'source_sha256': hashlib.sha256(raw).hexdigest()})
        hours = sum(w['lifetime_seconds'] for w in workers) / 3600
        rows.append({'route': route, 'new_independently_admitted_tasks_in_this_sample': accepted,
                     'sandbox_hours': hours, 'list_rate_subtotal_usd': hours * RATE,
                     'sample_compute_subtotal_per_new_admission_usd': hours * RATE / accepted,
                     'workers': workers})
    return {'stage': 'partial_measured_compute_samples_not_full_cost_per_task',
            'observed_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'pricing_source': 'https://www.daytona.io/pricing', 'pricing_checked_date': '2026-10-19',
            'resource_basis': '2 vCPU, 4 GiB RAM, 10 GiB storage; conservatively charge all storage without deducting advertised free storage or account credits',
            'cpu_usd_per_hour': 0.0504, 'ram_gib_usd_per_hour': 0.0162,
            'storage_gib_usd_per_hour': 0.000108, 'sandbox_usd_per_hour': RATE,
            'rows': rows,
            'includes': ['Recorded selected continuation generation and independent-control sandbox lifetimes', 'Failed and rejected cases within the listed selected runs, including observer/capture retries'],
            'excludes': ['First-pass allocations', 'Blind solver evaluation', 'Marin conversion/runtime experiments', 'Storage outside these lifetimes', 'Uncaptured lifecycle overhead', 'Codex and human development/review effort'],
            'free_allocations': 'Existing GLM endpoint and allocated TRC/CoreWeave CPU have zero incremental charge under user-reported access; not general public-service pricing.',
            'actual_invoices_or_credit_balance_verified': False,
            'production_cost_per_accepted_task_established': False,
            'scaling_formula': '(all generation, failed-candidate, validation, storage and required review costs) / independently accepted tasks, with solver evaluation and one-time engineering reported separately',
            'no_accepted_tasks': 'Cost per accepted task is not estimable where the denominator is zero; this is not a zero-cost success.'}


if __name__ == '__main__':
    data = build()
    (ROOT / 'compute-cost-samples.json').write_text(json.dumps(data, indent=2) + '\n')
    print(json.dumps({'hourly_rate': data['sandbox_usd_per_hour'], 'samples': [{k:v for k,v in r.items() if k != 'workers'} for r in data['rows']]}))
