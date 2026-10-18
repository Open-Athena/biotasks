"""Track the original three-task target for every route/repository or seed cohort."""
import csv
import datetime
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
FIRST = ROOT.parent


def build():
    raw = (FIRST / 'evidence/campaign-census-20261018/census.json').read_bytes()
    census = json.loads(raw)
    rows = []
    admissions_path = ROOT / 'new-admissions.json'
    new_admissions = json.loads(admissions_path.read_text()) if admissions_path.exists() else {}
    for unit in census['units']:
        route = unit['route']
        key = unit['unit_id']
        status = unit['applicability_status']
        admitted = unit['current_admitted_count'] + len(new_admissions.get(key, []))
        target = 3
        charge = None
        cap_note = 'Candidate-stage counters require route-specific reconciliation before further dispatch.'
        next_action = 'Reconcile remaining inputs/candidate allowance, then generate, independently validate and blind-solve missing tasks.'
        if status in ('unsupported_language', 'unsupported_profile'):
            target = None
            action = 'unsupported_native_language_or_profile'
            next_action = 'Outside native applicability; any language/profile port is a separate intervention.'
        elif admitted >= 3:
            action = 'target_met_for_declared_native_reward'
            next_action = 'Retain typed reward and lineage; no extra candidate or repeated blind attempt.'
        elif status == 'model_blocker' or route == 'optimization_synth/frontiersmith':
            action = 'blocked_native_model_support'
            next_action = 'GLM-only baseline blocked; no paid-model fallback. Record an explicit model-client port separately if undertaken.'
        elif status == 'native_controller_backend_and_isolation_blocker':
            action = 'blocked_backend_and_reference_isolation'
            next_action = 'Evaluate TRC caller Docker availability before any new native equivalence attempt; learner-visible reference remains an admission limitation.'
        elif status in ('test_parser_adapter_needed', 'native_test_layout_incompatible'):
            action = 'blocked_native_test_profile'
            next_action = 'Native test-profile/parser support missing; do not count unsupported execution as a generated failure.'
        elif status == 'no_native_advisories' or route == 'terminal_reconstruct/terminalworld':
            action = 'blocked_eligible_input_or_terms'
            next_action = 'Eligible native input/provenance gate must be resolved before authoring.'
        elif status == 'first_pass_inconclusive_capture_failure':
            action = 'capture_inconclusive_allowance_consumed'
            charge = 10
            cap_note = 'Actual counts unknown; original ten-candidate allowance conservatively consumed.'
            next_action = 'Recover original evidence if possible; do not reset or repeat unknown allowance.'
        elif route == 'equivalence_tests/r2e' or route == 'terminal_synth/endless_terminals':
            action = 'candidate_cap_exhausted_below_target'
            charge = 10
            cap_note = 'Ten native candidate attempts recorded; zero accepted tasks is a bounded negative outcome.'
            next_action = 'No automatic cap reset or post-hoc answer repair; preserve negative result.'
        else:
            action = 'target_not_met_work_remaining'
        if route == 'pr_diff/native':
            charge = 10
            cap_note = 'Ten considered PR inputs recorded per repository; selected three similarity tasks each admitted and scored.'
        if route == 'repo_mutate/swe_smith':
            charge = 4 if unit['repository'] == 'biopython/biopython' else 3
            cap_note = 'Exact first-pass mutation attempts; authoring/revalidation of the same saved IDs is not new candidate discovery.'
            if unit['repository'] == 'scikit-bio/scikit-bio':
                current = ROOT / 'skbio-contrast-01/generation.json'
                if current.exists():
                    data = json.loads(current.read_text())
                    charge += data['attempted']
                    cap_note += ' Continuation native attempts included; contrasts are not admissions.'
            next_action = 'Continue frozen remaining-allowance mutation cohort, then author/review/control/admit and one blind solve until three admissions or cap/budget stop.'
        if route == 'reasoning_synth/scaler':
            charge = 3
            cap_note = 'Three independently admitted synthetic task instances, one family; native reward -1/+1. Marin range metadata unresolved.'
        rewards = sorted({x['reward_semantics'] for x in unit['current_admissions']})
        rows.append({'unit_id': key, 'route': route, 'repository': unit['repository'], 'input_cohort': unit['cohort'], 'target': target, 'first_pass_admitted': unit['current_admitted_count'], 'new_admitted': len(new_admissions.get(key, [])), 'total_admitted': admitted, 'shortfall': max(0, target-admitted) if target is not None else None, 'first_pass_blind_attempts': unit['completed_blind_count'], 'candidate_cap': 10, 'charged_candidate_attempts': charge, 'remaining_candidate_allowance': max(0, 10-charge) if charge is not None else None, 'candidate_charge_note': cap_note, 'state': action, 'next_action': next_action, 'native_reward_semantics': rewards, 'original_status': status, 'first_pass_sources': [r['source'] for r in unit['generation_records']]})
    return {'observed_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'stage': 'full_original_target_tracking_not_a_completion_claim', 'target_policy': 'Three independently validated tasks per applicable route/repository; seed routes have named input cohorts. Maximum ten candidate attempts per unit, with original operational budget stops. Unsupported native language/profile cells have no native target; blocked cells retain explicit shortfall.', 'first_pass_census_sha256': hashlib.sha256(raw).hexdigest(), 'rows': rows, 'completion_proven': False, 'limitations': ['Only native patch-similarity admission is established for PR-diff; it is not functional correctness.', 'Unknown attempt totals are not zero or permission to dispatch; reconcile the route-specific candidate definition and receipts first.', 'This table is not a retrospective claim that aggregate N was frozen before the original launch.', 'No new admissions are inferred from controller success, executable contrasts, authored instructions or exports.']}


if __name__ == '__main__':
    result = build()
    (ROOT / 'target-tracker.json').write_text(json.dumps(result, indent=2) + '\n')
    fields = ['unit_id', 'route', 'repository', 'input_cohort', 'target', 'first_pass_admitted', 'new_admitted', 'total_admitted', 'shortfall', 'candidate_cap', 'charged_candidate_attempts', 'remaining_candidate_allowance', 'state', 'next_action']
    with (ROOT / 'target-tracker.csv').open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator='\n', extrasaction='ignore')
        writer.writeheader()
        writer.writerows(result['rows'])
    lines = ['# Three-task target tracker', '', 'Current admissions count independent validation, not raw exports. PR-diff admissions preserve patch-similarity semantics. Native language/profile exclusions and model/backend/input blockers remain explicit. Each seed recipe has a separate named cohort. The goal is not complete.', '', '| Route / recipe | Biopython | scikit-bio | bedtools2 | DESeq2 |', '| --- | --- | --- | --- | --- |']
    repos = ['biopython/biopython', 'scikit-bio/scikit-bio', 'arq5x/bedtools2', 'thelovelab/DESeq2']
    for route in dict.fromkeys(x['route'] for x in result['rows'] if x['repository']):
        cells = []
        for repo in repos:
            row = next(x for x in result['rows'] if x['route'] == route and x['repository'] == repo)
            if row['target'] is None:
                cell = 'unsupported'
            else:
                cell = str(row['total_admitted']) + '/3'
                if row['state'].startswith('blocked_'): cell += ' (blocked)'
                if row['state'] == 'capture_inconclusive_allowance_consumed': cell += ' (capture unknown; cap consumed)'
                if row['state'] == 'candidate_cap_exhausted_below_target': cell += ' (cap reached)'
            cells.append(cell)
        lines.append('| ' + route + ' | ' + ' | '.join(cells) + ' |')
    lines += ['', '| Seed route / recipe | Named input cohort | Independently admitted | State |', '| --- | --- | --- | --- |']
    for row in result['rows']:
        if not row['repository']:
            lines.append('| ' + row['route'] + ' | ' + row['input_cohort'] + ' | ' + str(row['total_admitted']) + '/3 | ' + row['state'] + ' |')
    lines += ['', 'The [CSV](target-tracker.csv) and [JSON](target-tracker.json) retain per-unit caps, shortfalls, source records and next actions. Unknown counts must be resolved before new dispatch. First-pass historical captures, retrospective aggregate N and billing limitations remain documented.']
    (ROOT / 'target-tracker.md').write_text('\n'.join(lines) + '\n')
    print(json.dumps({'tracked_units': len(result['rows']), 'repository_routes': len({x['route'] for x in result['rows'] if x['repository']}), 'seed_cohorts': sum(x['repository'] is None for x in result['rows']), 'target_met_units': sum(x['target'] is not None and x['shortfall'] == 0 for x in result['rows']), 'completion_proven': False}))
