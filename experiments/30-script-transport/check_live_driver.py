"""Offline checks of orchestration, not biological recovery or Docker evidence."""
import errno
import json
from pathlib import Path
import tempfile

import live_validation as driver


def main():
    original, _, _, validator = driver.load_sources()
    manifest = driver.verify_inputs(validator)
    rows = []
    for mode in ('complete', 'timeout', 'e2big'):
        case = manifest['cases'][0]
        with tempfile.TemporaryDirectory(prefix='biotasks30-driver-') as directory:
            output = Path(directory)

            class Fake:
                def __init__(self):
                    self.stages = []

                def exec(self, command, *, timeout=300):
                    checksum = driver.digest(command.encode())
                    stage = next((name for name, info in case['stages'].items()
                                  if checksum == info['sha256']), None)
                    if stage:
                        self.stages.append(stage)
                        if mode == 'timeout':
                            return original.ExecResult(124, 'partial output', 'timeout', 0)
                        if mode == 'e2big' and stage == 'post':
                            raise OSError(errno.E2BIG, 'synthetic oversized argument')
                        state = 'FAILED' if stage == 'pre' else 'PASSED'
                        return original.ExecResult(0, 'R2E_START_TEST_OUTPUT\n'
                            f'tests/test_a.py::test_a {state} [100%]\n'
                            'R2E_END_TEST_OUTPUT\n', '', 0)
                    return original.ExecResult(0, 'OK\n', '', 0)

            fake = Fake()
            recorder = driver.RecordedSandbox(fake, output, case)
            outcome, exception = None, None
            try:
                outcome = validator.validate_pr(sandbox=recorder, base_commit=case['base_sha'],
                    patch=(driver.ROOT/'inputs-private'/'958-source.patch').read_text(),
                    test_patch=(driver.ROOT/'inputs-private'/'958-test.patch').read_text(),
                    test_cmds=case['commands'], language='python', timeout=600)
            except (driver.ArmTimeout, OSError) as error:
                exception = error
            if mode == 'complete':
                assert outcome.status == 'verified'
                assert outcome.fail_to_pass == ['tests/test_a.py::test_a']
                assert fake.stages == ['pre', 'post']
            elif mode == 'timeout':
                assert isinstance(exception, driver.ArmTimeout)
                assert fake.stages == ['pre']  # no post-stage after timeout
                assert recorder.calls[-1]['exit_code'] == 124
            else:
                assert exception.errno == errno.E2BIG
                assert fake.stages == ['pre', 'post']
                assert recorder.calls[-1]['errno'] == errno.E2BIG
            assert json.loads((output/'calls.json').read_text()) == recorder.calls
            rows.append({'mode': mode, 'stage_calls': fake.stages, 'assertions_passed': True})
        assert not output.exists()
    report = {'scope': 'Synthetic executor through full pinned validate_pr and recorded adapter',
              'cases': rows, 'private_temporary_outputs_removed': True,
              'limitations': ['No Docker or biological execution',
                             'Container cleanup and supervisor deadline require live validation']}
    (driver.ROOT/'live-driver-check.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report))


if __name__ == '__main__':
    main()
