"""Summarize retained native records without rerunning a pipeline or model."""
import collections
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
EV = ROOT / 'evidence'


def load(path):
    return json.loads(path.read_text())


def main():
    windows = load(EV / 'native-windows.json')
    lifecycle = load(EV / 'lifecycle.json')
    cleanup = load(EV / 'supervisor-result.json')
    exports = load(EV / 'exported-tasks.json')
    assert lifecycle['all_terminal']
    assert not exports and not list((EV / 'native/outputs').rglob('task.toml'))
    assert all(not cleanup[k] for k in ['remaining_containers', 'remaining_controllers', 'remaining_images'])
    repos = []
    for slug, repo in [('MLCIL__scikit-fingerprints-544', 'MLCIL/scikit-fingerprints'),
                       ('nipy__nipype-3753', 'nipy/nipype'), ('psychopy__psychopy-7475', 'psychopy/psychopy')]:
        log = (EV / f'{slug}.txt').read_text()
        actions = re.findall(r'step=(\d+) action=(\w+)', log)
        assert [int(i) for i, _ in actions] == list(range(len(actions)))
        counts = dict(collections.Counter(a for _, a in actions))
        folder = EV / 'native/bootstrap' / repo.replace('/', '__')
        transcript = next(folder.rglob('transcript.jsonl'))
        rows = [json.loads(line) for line in transcript.read_text().splitlines()]
        bootstrap_files = list(folder.rglob('bootstrap.json'))
        cached = load(bootstrap_files[0]) if bootstrap_files else None
        record = {'repository': repo, 'agent_iterations': len(actions), 'actions': counts,
                  'transcript_entries': len(rows), 'bootstrap_saved': bool(cached),
                  'native_estimated_cost_usd': 0.0, 'billed_cost_usd': None,
                  'stop_reason': 'saved_native_bootstrap' if cached else 'hit max_iterations=20'}
        if cached:
            assert cached['iterations'] == len(actions)
            record.update({k: cached[k] for k in ['image_tag', 'image_digest', 'verify_passed', 'verify_detail', 'test_cmds']})
        else:
            assert 'hit max_iterations=20' in log
        repos.append(record)
    metadata = load(EV / 'nipype-selected-metadata.json')
    native_log = (EV / 'nipy__nipype-3753.txt').read_text()
    bases = re.findall(r'running pre-fix stage at ([0-9a-f]+)', native_log)
    assert native_log.count('parsed pre=0 post=0 tests; f2p=0 p2p=0') == len(bases) == 2
    assert 'candidates  6' in native_log and "'no_test_patch': 4, 'no_fail_to_pass': 2" in native_log
    cases = []
    baseline = {(x['repository'], x['number']): x for x in load(EV / 'baseline-24-outcomes.json')['cases']}
    for window in load(ROOT / 'selection-preflight.json')['windows']:
        for number in window['matching_numbers']:
            repo = window['repository']
            row = {'repository': repo, 'number': number, 'comparison_input': (repo, number) in baseline,
                   'native_selection_reached': repo == 'nipy/nipype', 'exported': False}
            if repo == 'nipy/nipype':
                pr = next(x for x in metadata if x['number'] == number)
                test_files = [f['path'] for f in pr['files'] if '/tests/' in f['path']]
                validated = bool(test_files) and any(pr['baseRefOid'].startswith(b) for b in bases)
                row.update(disposition='native_rejected' if validated else 'native_filtered',
                           reason='no_fail_to_pass' if validated else 'no_test_patch',
                           native_validation_reached=validated,
                           attribution='Native aggregate outcomes mapped using recorded base SHAs and public PR file metadata; plain logs do not enumerate every skipped PR.')
                if validated:
                    row.update(parsed_pre_tests=0, parsed_post_tests=0, fail_to_pass_count=0, pass_to_pass_count=0)
            else:
                row.update(disposition='bootstrap_unresolved', reason='shared_repository_bootstrap_exhausted_turn_limit', native_validation_reached=False)
            if row['comparison_input']:
                old = baseline[repo, number]
                row['baseline_24'] = {k: old[k] for k in ['automatic_disposition', 'reason', 'pass_to_pass_count'] if k in old}
            cases.append(row)
    assert len(cases) == 16 and sum(x['comparison_input'] for x in cases) == 5
    result = {'status': 'completed_negative_for_tested_configuration', 'upstream_source_modifications': [],
              'native_windows': windows, 'repositories': repos, 'cases': cases,
              'counts': {'planned_prs_before_filters': len(cases), 'comparison_prs': 5, 'additional_prs': 11,
                         'native_selected': sum(x['native_selection_reached'] for x in cases),
                         'native_filtered_no_test_patch': sum(x.get('reason') == 'no_test_patch' for x in cases),
                         'native_validations': sum(x['native_validation_reached'] for x in cases),
                         'native_validation_rejections': 2, 'bootstrap_unresolved_prs': 10,
                         'exports': len(exports), 'base_reference_grading_runs': 0, 'verified_tasks': 0,
                         'agent_iterations': sum(x['agent_iterations'] for x in repos),
                         'invalid_actions': sum(x['actions'].get('INVALID', 0) for x in repos)},
              'cost': {'allocated_cpu_hours': lifecycle['total_allocated_cpu_hours'],
                       'native_estimated_model_usd': 0.0, 'billed_model_usd': None,
                       'api_request_count_including_sdk_retries': None, 'token_usage': None,
                       'note': 'Zero native estimates are not evidence of zero charges. Native records omit request IDs, token usage and billed costs; the $5 estimated guard was not an effective billing bound. Agent iterations remain bounded. Interactive Codex and engineering costs are not measured.'},
              'cleanup': cleanup, 'grading': 'Not applicable: no task.toml was exported. No solver or extra LLM call was used.'}
    (EV / 'final-outcomes.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result['counts'], indent=2))


if __name__ == '__main__':
    main()
