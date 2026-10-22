"""Reconcile retained discovery lists; never fetch, select or validate another PR."""

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--state-dir', type=Path, required=True)
    args = parser.parse_args()
    rows = []
    for selected in json.loads((ROOT / 'cohort.json').read_text()):
        slug = selected['slug']
        window = {pr['number'] for pr in json.loads((ROOT / 'preflight' / (slug + '-window.json')).read_text())}
        newest = {pr['number'] for pr in json.loads((ROOT / 'preflight' / (slug + '-newest300.json')).read_text())}
        assert len(window) == selected['window_count']
        run = 'biotasks28-' + slug.lower().replace('__', '-') + '-001'
        path = args.state_dir / (run + '-results') / 'expanded/native-observations/native-candidates.json'
        row = {'repo': selected['repo'], 'complete_window_merged': len(window),
            'preflight_newest300_in_window': len(window & newest),
            'preflight_window_outside_newest300': sorted(window - newest),
            'actual_native_list_available': path.exists(),
            'actual_native_returned': None, 'actual_window_missing_from_native': None}
        if path.exists():
            original = json.loads(path.read_text())
            native = {pr['number'] for pr in original}
            assessment = json.loads((args.state_dir / (run + '-results') / 'assessment.json').read_text())
            entered = set(assessment['candidate_pr_numbers_entered'])
            assert len(native) == len(original) == assessment['native_candidates_returned']
            assert entered <= native
            row.update(actual_native_returned=len(native),
                actual_native_in_window=len(native & window),
                actual_window_missing_from_native=sorted(window - native),
                actual_native_outside_window=sorted(native - window),
                actual_native_entered=assessment['candidates_entered'],
                actual_native_returned_but_not_entered=sorted(native - entered))
        rows.append(row)
    report = {'method': 'Set reconciliation of original preflight complete-window/newest-300 snapshots and actual native returned lists only. No GitHub queries, reruns, replacement PRs or selection changes.',
        'limits': 'Preflight newest-300 is a snapshot, not the actual run fetch. Missing native PRs can reflect later merge drift, native limit/base-SHA lookup or other upstream discovery rules; absence alone does not identify which. An unavailable list is not zero PR suitability. Returned/entered counts do not establish paired validation or task yield.',
        'repositories': rows}
    (ROOT / 'results/candidate-coverage.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps([{'repo': r['repo'], 'window': r['complete_window_merged'],
        'preflight_in_newest300': r['preflight_newest300_in_window'],
        'native_returned': r['actual_native_returned']} for r in rows], indent=2))


if __name__ == '__main__':
    main()
