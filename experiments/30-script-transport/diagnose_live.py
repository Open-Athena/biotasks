"""Bind transport conclusion and deleted-target diagnosis to original live outputs."""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def main():
    readback = json.loads((ROOT/'live-readback.json').read_text())
    assert readback['cleanup_verified']
    manifest = json.loads((ROOT/'live-script-manifest.json').read_text())
    failed_case = next(row for row in manifest['cases'] if row['pr'] == 958)
    patch = (ROOT/'inputs-private/958-test.patch').read_text()
    deleted = [block.splitlines()[0].split(' b/', 1)[1]
               for block in re.split(r'(?=^diff --git )', patch, flags=re.M)
               if '\n+++ /dev/null\n' in block]
    assert len(deleted) == 2
    assert all(path in failed_case['test_files'] and path in failed_case['commands'][0]
               for path in deleted)
    directory = ROOT/'inputs-private/live-001/comparison'
    a, b = [json.loads((directory/f'671-{name}/outcome-private.json').read_text())
            for name in ('original', 'stdin')]
    assert a['fail_to_pass'] == b['fail_to_pass'] and a['pass_to_pass'] == b['pass_to_pass']
    arms = {(row['pr'], row['transport']): row for row in readback['arms']}
    assert arms[958, 'original']['errno'] == 7
    assert arms[958, 'stdin']['status'] == 'failed'
    errors = []
    for row in arms[958, 'stdin']['stages']:
        out = directory/'958-stdin'/f"call-{row['index']:02d}-stdout.txt"
        text = out.read_text()
        assert 'ERROR: file or directory not found: '+deleted[0] in text
        assert 'collected 0 items' in text
        errors.append({'stage': row['stage'], 'outer_exit_code': row['exit_code'],
                       'tests_collected': 0, 'missing_target': deleted[0],
                       'stdout_sha256': row['stdout_sha256']})
    report = {'failed_pr': 958, 'successful_control_pr': 671,
              'original_errno7_reproduced': True,
              'candidate_delivers_both_stages': len(errors) == 2,
              'candidate_native_status': 'failed', 'candidate_f2p_count': 0,
              'deleted_test_targets': deleted, 'candidate_stage_evidence': errors,
              'control_exact_f2p_and_p2p_equal': True,
              'control_f2p_count': len(a['fail_to_pass']), 'control_p2p_count': len(a['pass_to_pass']),
              'cleanup_verified': True, 'model_calls': 0,
              'conclusion': 'Transport exception removed; deleted-file targeting still prevents PR958 validation. Successful control preserves native test sets.',
              'limits': ['No PR958 task recovered, export generated or independent Harbor control added',
                         'Original pinned validator/parser unchanged; no deleted-target repair applied',
                         'Native outer exit 0 does not imply successful pytest command',
                         'Reconstruction dependency drift and missing original failed script bytes remain']}
    (ROOT/'live-diagnosis.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report))


if __name__ == '__main__':
    main()
