"""Audit authored binary native grades against retained JUnit evidence."""

import json
import xml.etree.ElementTree as ET

from audit_history_blind_batch import audit, file_sha


def binary_grade(root, _f2p, _p2p):
    details = json.loads((root / 'verifier/result.json').read_text())
    result = json.loads((root / 'result.json').read_text())
    cases = list(ET.parse(root / 'verifier/results.xml').iter('testcase'))
    assert cases and result['exception_info'] is None
    passed = sum(not any(c.find(tag) is not None for tag in ('failure', 'error', 'skipped')) for c in cases)
    statuses = details['statuses']
    assert len(cases) == len(statuses)
    assert passed == sum(v == 'passed' for v in statuses.values())
    computed = int(passed == len(cases) and details['returncode'] == 0)
    assert bool(computed) == details['passed']
    reward = float((root / 'verifier/reward.txt').read_text())
    assert computed == reward == result['verifier_result']['rewards']['reward']
    return {'reward': reward, 'tests_passed': passed, 'tests_total': len(cases),
            'native_command_exit_code': details['returncode'],
            'junit_sha256': file_sha(root / 'verifier/results.xml'),
            'native_grade_sha256': file_sha(root / 'verifier/result.json'),
            'original_trial_result_sha256': file_sha(root / 'result.json')}


def audit_authored(recovered, inputs, manifest, checksum_function):
    result = audit(recovered, inputs, manifest, checksum_function, binary_grade, expected_sandboxes=6)
    result['stage'] = 'native_authored_batch_results_audited_public_and_independent_cleanup_gates_separate'
    return result
