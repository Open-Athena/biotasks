"""Offline checks of the unchanged native two-stage validation call."""

import argparse
from pathlib import Path

from repo2rlenv.bootstrap.docker import ExecResult
from repo2rlenv.execution.lifecycle import save_record
from validate_code_instruct import validate_one


class SandboxFixture:
    def __init__(self, outputs):
        self.outputs = iter(outputs)
        self.calls = 0

    def exec(self, command, *, timeout):
        assert timeout == 180
        self.calls += 1
        return next(self.outputs)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    candidate = {'test_filename': 'test_r2e_0123456789.py', 'problem': 'Fixture',
                 'test_code': 'assert False', 'solution_code': 'fixture = 1'}
    passed = ExecResult(0, '1 passed in 0.01s', '', 0.01)
    failed = ExecResult(0, '1 failed in 0.01s', '', 0.01)
    cases = [
        ('contrast', [failed, passed], True, ''),
        ('already_passes', [passed], False, 'test_passes_without_oracle'),
        ('reference_fails', [failed, failed], False, 'oracle_does_not_satisfy_test'),
    ]
    results = []
    for name, outputs, accepted, reason in cases:
        sandbox = SandboxFixture(outputs)
        outcome = validate_one(sandbox, candidate, args.output / name)
        assert outcome.accepted is accepted and outcome.reason == reason
        assert sandbox.calls == len(outputs)
        assert len(list((args.output / name).glob('command-*.json'))) == len(outputs)
        results.append({'case': name, 'native_accepted': outcome.accepted, 'calls': sandbox.calls})
    save_record(args.output / 'checks.json', {'stage': 'offline_validation_contract',
        'model_calls': 0, 'containers_started': 0, 'records': results,
        'limitation': 'Synthetic command outputs verify wiring, not candidate correctness.'})
    print('Three native validation paths and full command-log recording verified')


if __name__ == '__main__':
    main()
