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
    counter_path = ROOT / 'remaining-candidate-reconciliation.json'
    reconciled = json.loads(counter_path.read_text())['units'] if counter_path.exists() else {}
    for counter in reconciled.values():
        charged = 0
        for receipt in counter['receipts']:
            source = (FIRST / receipt['source']).read_bytes()
            assert hashlib.sha256(source).hexdigest() == receipt['sha256']
            value = json.loads(source)[receipt['counter_key']]
            assert value == receipt['charged']
            charged += value
        assert charged == counter['charged_candidate_attempts'] <= 10
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
        if route == 'pr_runtime/native' and unit['repository'] == 'scikit-bio/scikit-bio':
            selection = ROOT / 'pr-runtime-next/manifest.json'
            if selection.exists():
                planned = json.loads(selection.read_text())
                charge = planned['conservative_allowance_after_selection']
                numba_profile = ROOT / 'pr-runtime-skbio-numba-next/manifest.json'
                if numba_profile.exists():
                    charge = json.loads(numba_profile.read_text())['conservative_allowance_after_selection']
                cap_note = 'Conservative charge: two historical native execution profiles for one PR2633 lineage, plus frozen PR2630/2636 selected inputs. New selection counts even if a native filter/execution rejects it; no reset or new independent lineage inferred from repeat profiles.'
                next_action = 'Use retained native exports: PR2630 needs portable full/partial/incorrect/alternative graded controls; PR2636 original CPU profile is unaccepted, with separately planned optional Numba CPU coverage. Blind solving awaits approved model connectivity.' if (ROOT / 'skbio-pr-runtime-native-01/recovery.json').exists() else 'Run frozen model-free native PR cohort, then independent validation.'
        if route == 'pr_runtime/native' and unit['repository'] == 'biopython/biopython':
            selection = ROOT / 'pr-runtime-biopython-intake/additional-selection.json'
            if selection.exists():
                considered = json.loads(selection.read_text())
                charge = considered['cumulative_conservative_charge']
                cap_note = 'One original PR5148 input, three newer matched similarity inputs rejected by native no-test-patch filter, then five fixed historical inputs; selection counts once including filter rejects. Saved eligible PR5316 is not a new charge if later materialized.'
                next_action = 'Native PR5317/5310/5308 exported. PR5310 instruction/oracle mismatch rejected; QCP5317 and hash5308 need portable graded controls. PR5316 remains selected/eligible/unmaterialized plus one additional new-input allowance; no cap reset.' if (ROOT / 'biopython-pr-runtime-native-01/recovery.json').exists() else 'Execute frozen PR5317/5310/5308 native cohort, then review portable controls and instructions.'
        if route == 'pr_runtime/native' and new_admissions.get(key):
            if unit['repository'] == 'scikit-bio/scikit-bio':
                next_action = 'PR2630 admitted after six portable graded controls; original PR2633 retained. Third task still needed: separate Numba PR2636 native export needs instruction/coverage review and independent controls. Two profiles of PR2636 count at most one source task. All new blind attempts await approved GLM connectivity.'
            elif unit['repository'] == 'biopython/biopython':
                next_action = 'QCP5317 and SimpleLocation5308 admitted after six portable graded controls each. PR5310 original contract mismatch remains rejected. Saved eligible PR5316 remains available for first native materialization without a new selection charge; one additional new-input allowance remains. All new blind attempts await approved GLM connectivity.'
        if route == 'pr_runtime/native' and unit['repository'] == 'biopython/biopython' and (ROOT / 'biopython-pr-saved-native-01/recovery.json').exists():
            next_action = 'QCP5317 and SimpleLocation5308 admitted (2/3). Saved PR5316 first materialization completed with 4F2P/21P2P; independent portable controls prepared. Cap charge remains9/10, no new selection for materialization. Original PR5310 instruction mismatch remains rejected; new blind attempts await approved GLM connectivity.'
        if route == 'pr_diff/native':
            charge = 10
            cap_note = 'Ten considered PR inputs recorded per repository; selected three similarity tasks each admitted and scored.'
        if route == 'repo_mutate/swe_smith':
            charge = 4 if unit['repository'] == 'biopython/biopython' else 3
            cap_note = 'Exact first-pass mutation attempts; authoring/revalidation of the same saved IDs is not new candidate discovery.'
            prefix = 'biopython' if unit['repository'] == 'biopython/biopython' else 'skbio'
            current = ROOT / (prefix + '-contrast-01/generation.json')
            small_summary = ROOT / (prefix + '-smith-continuation-01-small-summary.json')
            if current.exists():
                data = json.loads(current.read_text())
                charge += data['attempted']
                cap_note += ' Continuation native generation attempts included; contrasts are not admissions.'
            elif small_summary.exists():
                data = json.loads(small_summary.read_text())
                assert data['generation_available'] and data['model_calls'] == 0
                charge += data['attempted']
                cap_note += ' Continuation counters from captured controller summary; full archive recovery/public preservation pending. Contrasts are not admissions.'
            assert charge <= 10
            next_action = 'Continue frozen remaining-allowance mutation cohort, then author/review/control/admit and one blind solve until three admissions or cap/budget stop.'
            if charge == 10:
                action = 'candidate_cap_exhausted_below_target'
                next_action = 'No new candidate discovery. Preserve and independently assess pending saved contrast(s); cap remains ten and no new admission is inferred.'
        if route == 'repo_reconstruct/swe_flow':
            counters_path = ROOT / 'flow-candidate-counters.json'
            if counters_path.exists():
                counters = json.loads(counters_path.read_text())
                prefix = 'biopython-flow-' if unit['repository'] == 'biopython/biopython' else 'skbio-flow-'
                charge = sum(x['generation']['attempted'] for x in counters['runs'] if x['run'].startswith(prefix))
                cap_note = 'Exact saved native generation counters agree with events: empty Biopython trace run 0, adapted Biopython 3, scikit-bio 3. Prior authoring/export reuses saved identities.'
                prefix = 'biopython' if unit['repository'] == 'biopython/biopython' else 'skbio'
                current = ROOT / (prefix + '-flow-contrast-01/generation.json')
                small_summary = ROOT / (prefix + '-flow-continuation-01-small-summary.json')
                if current.exists():
                    charge += json.loads(current.read_text())['attempted']
                    cap_note += ' Continuation original generation attempts included; no admission inferred.'
                elif small_summary.exists():
                    charge += json.loads(small_summary.read_text())['attempted']
                    cap_note += ' Captured continuation controller summary included; full recovery/publication pending.'
                assert charge <= 10
                next_action = 'Use native exclusion IDs and remaining allowance for new development steps; independently review instructions and validate graders before admission.'
        if route == 'reasoning_synth/scaler':
            charge = 3
            cap_note = 'Three independently admitted synthetic task instances, one family; native reward -1/+1. Marin range metadata unresolved.'
        if key in reconciled:
            assert target is not None
            counter = reconciled[key]
            charge = counter['charged_candidate_attempts']
            cap_note = counter['definition'] + ' Exact source hashes and counter keys are retained in remaining-candidate-reconciliation.json.'
            next_action = 'Continue from reconciled remaining candidate allowance with new frozen eligible inputs; assess retained exports first. Preserve rejected originals and native repair limits, then independently validate and run one blind attempt per admission.'
        if target is not None and admitted >= target:
            next_action = 'Three-task target met for the declared native reward. No further candidate discovery for this unit; retain lineage and complete only pending single blind attempts or declared integration gates.'
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
