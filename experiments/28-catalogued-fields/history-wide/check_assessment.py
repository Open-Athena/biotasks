"""Offline coverage, original-parser/control consistency and streaming evidence checks."""

import hashlib
import gzip
import io
import json
from pathlib import Path
import tarfile
from tempfile import TemporaryDirectory

from assess_history import reconcile_identities, scan_phase, trial, verified, verifier_module


def main():
    ids = [5, 4, 3, 2, 1]
    ledger = {'state': 'running', 'backlog_pr_numbers': [3, 2, 1], 'batches': [
        {'index': 0, 'state': 'completed', 'selected_pr_numbers': ids},
        {'index': 1, 'state': 'running', 'selected_pr_numbers': [3, 2, 1]}]}
    observed = {'batch-0000': {'returned': ids, 'events': [
        {'event': 'candidate_entered', 'pr': 5}, {'event': 'candidate_entered', 'pr': 4}]},
        'batch-0001': {'returned': [3, 2, 1], 'events': [{'event': 'candidate_entered', 'pr': 3}]}}
    coverage = reconcile_identities(ids, ledger, observed)
    assert coverage['native_entered_pr_numbers'] == [5, 4, 3]
    assert coverage['backlog_count'] == 2 and coverage['original_parent_backlog_count'] == 3
    assert coverage['parent_checkpoint_censored'] and coverage['complete_identity_accounting']
    assert coverage['native_unique_returned_count'] == 5 and coverage['native_returned_appearances'] == 8
    assert coverage['returned_but_unentered_pr_numbers'] == [2, 1]
    omitted = reconcile_identities(ids, {'state': 'bounded_with_backlog', 'backlog_pr_numbers': [4, 3, 2],
        'batches': [{'index': 0, 'state': 'completed', 'selected_pr_numbers': ids}]},
        {'batch-0000': {'returned': [5, 4, 3, 2], 'events': [{'event': 'candidate_entered', 'pr': 5}]}})
    assert omitted['native_discovery_omitted_pr_numbers'] == [1] and omitted['backlog_count'] == 3
    observed['batch-0001']['events'] = [{'event': 'candidate_entered', 'pr': 4}]
    try:
        reconcile_identities(ids, ledger, observed)
    except AssertionError:
        pass
    else:
        raise AssertionError('Duplicate/non-selected entry not rejected')
    module, expected = verifier_module()
    with TemporaryDirectory(prefix='history-assessment-check-') as scratch:
        root = Path(scratch); task = root / 'outputs/example/example-1'; tests = task / 'tests'; tests.mkdir(parents=True)
        source = Path(__file__).parent.parent / 'preflight/upstream_verifier.py'
        (tests / 'verifier.py').write_bytes(source.read_bytes())
        f2p = ['tests/test_fix.py::test_fix']; p2p = ['tests/test_fix.py::test_keep']
        (tests / 'f2p.json').write_text(json.dumps(f2p)); (tests / 'p2p.json').write_text(json.dumps(p2p))
        controls = []
        for agent, state in [('nop', 'FAILED'), ('oracle', 'PASSED')]:
            directory = root / 'jobs/fresh' / ('example-1-' + agent) / 'trial'; verifier = directory / 'verifier'; verifier.mkdir(parents=True)
            text = f'tests/test_fix.py::test_fix {state}\ntests/test_fix.py::test_keep PASSED\ntests/test_other.py::test_warning FAILED\n'
            statuses = module.parse_logs('pytest', text); assert len(statuses) == 3
            details = module.grade(f2p, p2p, statuses, 'pytest')
            details.update(parse_status='ok', runner='pytest', tests_parsed=3, exit_code=1, command_resolved=False)
            (verifier / 'test_output.log').write_text(text)
            (verifier / 'reward.txt').write_text(str(details['reward']))
            (verifier / 'reward-details.json').write_text(json.dumps(details))
            result = directory / 'result.json'; result.write_text(json.dumps({'verifier_result': {'rewards': {'reward': details['reward']}}}))
            controls.append(trial(result, task, module, expected, True))
        assert verified(*controls, True)
        assert controls[1]['reward_details']['untracked_failed_count'] == 1
        assert not controls[1]['reward_details']['command_resolved']
        result.write_text(json.dumps({'exception_info': {'exception_type': 'VerifierTimeoutError'}, 'verifier_result': None}))
        timed = trial(result, task, module, expected, True)
        assert timed['reward'] is None and not verified(controls[0], timed, True)
        phase = root / 'fixture.tar.gz'
        files = {'outputs/example/example-1/task.toml': b'fixture',
            'outputs/example/example-1/tests/f2p.json': b'["fix"]',
            'outputs/example/example-1/solution/patch.diff': b'unchanged source patch',
            'outputs/example/metadata/index.json': b'{}',
            'native-observations/batch-0000/validation-001-pr-1.json.gz': gzip.compress(json.dumps({
                'status': 'failed', 'reason': 'fixture original validation',
                'fail_to_pass': [], 'pass_to_pass': ['kept']}).encode())}
        with tarfile.open(phase, 'w:gz') as archive:
            for name, raw in files.items():
                member = tarfile.TarInfo(name); member.size = len(raw); archive.addfile(member, io.BytesIO(raw))
        extract = root / 'selected-files'; extract.mkdir()
        observations, hashes, _, exports = scan_phase(phase, extract)
        assert observations['batch-0000']['validations'] == [{
            'file': 'native-observations/batch-0000/validation-001-pr-1.json.gz',
            'status': 'failed', 'reason': 'fixture original validation', 'f2p': 0, 'p2p': 1}]
        assert exports == ['outputs/example/example-1']
        assert set(hashes) == {'/work/outputs/example/example-1'}
        assert hashes['/work/outputs/example/example-1']['tests/f2p.json'] == hashlib.sha256(b'["fix"]').hexdigest()
        assert (extract / 'outputs/example/example-1/tests/f2p.json').read_bytes() == b'["fix"]'
    print('History assessment fixtures passed: deadline-censored parent ledger, unavailable discovery, no duplicate entries, exact original parser/grade evidence, shared untracked failures, timeout grade absence and forward-only archive hashing/extraction. No model/network/native test execution; scratch removed.')


if __name__ == '__main__':
    main()
