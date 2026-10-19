"""Attribute retained lifetimes through recorded cohort provenance, leaving gaps explicit."""
import collections
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def main():
    inventory = json.loads((HERE / 'worker-cost-evidence-inventory.json').read_text())
    census = json.loads((HERE.parent / 'evidence/campaign-census-20261018/census.json').read_text())
    samples = json.loads((HERE / 'compute-cost-samples.json').read_text())
    ledger = json.loads((HERE / 'consolidated-ledger.json').read_text())
    routes_by_cohort = collections.defaultdict(set)
    for unit in census['units']:
        records = [*unit['generation_records'], *unit.get('additional_stage_records', [])]
        for record in records:
            # These are explicit census provenance fields, not inferred name matches.
            # Saved authoring records point separately to native contrasts and exports.
            for key in ('source', 'contrast_source', 'export_source'):
                source = record.get(key, '')
                if source.startswith('evidence/'):
                    assert (HERE.parent / source).is_file(), source
                    routes_by_cohort[source.split('/')[1]].add(unit['route'])
    exact = {}
    for row in samples['rows']:
        for worker in row['workers']:
            assert worker['sandbox_id'] not in exact
            exact[worker['sandbox_id']] = row['route']
    continuation_sources = {
        'skbio-smith-remaining-01/contrast-summary.json': 'repo_mutate/swe_smith',
        'skbio-flow-remaining-01/contrast-summary.json': 'repo_reconstruct/swe_flow',
        'skbio-flow-gini-01/contrast-summary.json': 'repo_reconstruct/swe_flow',
        'authored-skbio-mm-native-01/controller-small-summary.json': 'repo_mutate/swe_smith',
        'authored-skbio-tsallis-native-01/controller-small-summary.json': 'repo_mutate/swe_smith',
    }
    source_hashes = {}
    for source, route in continuation_sources.items():
        raw = (HERE / source).read_bytes()
        source_hashes[source] = hashlib.sha256(raw).hexdigest()
        for worker in json.loads(raw)['workers']:
            identity = worker['worker_id']
            assert identity not in exact or exact[identity] == route
            exact[identity] = route
    rows = []
    for worker in inventory['workers']:
        identity = worker['worker_id']
        matches = set()
        sources = []
        for source in worker['sources']:
            cohort = source['relative_local_evidence_path'].split('/')[0]
            cohort = cohort.removesuffix('-recovered')
            if cohort in routes_by_cohort:
                matches.update(routes_by_cohort[cohort])
                sources.append(cohort)
        route = exact.get(identity)
        basis = 'exact_sandbox_id_in_reviewed_continuation_receipt' if route else None
        if not route and len(matches) == 1:
            route = next(iter(matches))
            basis = 'retained_archive_cohort_matches_first_pass_generation_provenance'
        if route and matches:
            assert matches == {route}
        resources = worker['resources']
        assert resources == {'provider': 'daytona', 'cpus': 2, 'memory_mb': 4096, 'disk_gb': 10}
        hours = worker['recorded_lifetime_seconds'] / 3600
        rows.append({'sandbox_id': identity, 'route': route, 'attribution_basis': basis,
                     'matching_generation_cohorts': sources, 'sandbox_hours': hours,
                     'list_rate_compute_usd': hours * samples['sandbox_usd_per_hour'],
                     'source_record_sha256': [x['original_sha256'] for x in worker['sources']]})
    totals = []
    accepted = collections.Counter(t['route'] for t in ledger['tasks'])
    all_routes = sorted({u['route'] for u in census['units']})
    for route in all_routes:
        selected = [r for r in rows if r['route'] == route]
        cost = sum(r['list_rate_compute_usd'] for r in selected)
        totals.append({'route': route, 'attributed_workers': len(selected),
                       'recorded_sandbox_hours': sum(r['sandbox_hours'] for r in selected),
                       'partial_recorded_compute_usd': cost if selected else None,
                       'accepted_tasks': accepted[route],
                       'partial_recorded_compute_per_accepted_task_usd': cost / accepted[route] if selected and accepted[route] else None,
                       'full_cost_established': False})
    result = {'stage': 'partial_route_attribution_not_full_production_cost', 'routes': totals,
              'workers': rows, 'unattributed_workers': sum(r['route'] is None for r in rows),
              'unattributed_sandbox_hours': sum(r['sandbox_hours'] for r in rows if r['route'] is None),
              'pricing_basis_source': 'compute-cost-samples.json',
              'continuation_receipt_sha256': source_hashes,
              'source_sha256': {name: hashlib.sha256((HERE / name).read_bytes()).hexdigest() for name in ['worker-cost-evidence-inventory.json', 'compute-cost-samples.json', 'consolidated-ledger.json', '../evidence/campaign-census-20261018/census.json']},
              'limitations': ['Generation cohort attribution is based on retained archive provenance, not provider invoice metadata.',
                             'Shared setup, ambiguous controls, and Marin integration remain unassigned rather than distributed arbitrarily.',
                             'Provider-direct solver/validation sandbox lifetimes are not all represented by worker lifecycle records.',
                             'Partial subtotals include failures within attributed lifetimes but do not establish full route costs.',
                             'Free-model latency, human/Codex work, storage outside recorded lifetimes and account credits are not priced.',
                             'Null means no attributable evidence or no accepted-task denominator, never zero-cost success.']}
    (HERE / 'route-compute-attribution.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'attributed': len(rows) - result['unattributed_workers'], 'unattributed': result['unattributed_workers'], 'routes_with_cost_evidence': sum(bool(r['attributed_workers']) for r in totals)}))


if __name__ == '__main__':
    main()
