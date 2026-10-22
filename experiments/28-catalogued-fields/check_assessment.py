"""Reject contradictory rewards, missing parser evidence and timeout artifacts."""

import json
from pathlib import Path
from tempfile import TemporaryDirectory

from assess import trial_evidence, verified_pair

with TemporaryDirectory() as directory:
    root = Path(directory)

    def trial(name, reward, *, written=None, detailed=None, exception=None, parse='ok'):
        path = root / name / 'result.json'
        path.parent.mkdir(exist_ok=True)
        verifier = path.parent / 'verifier';verifier.mkdir(exist_ok=True)
        path.write_text(json.dumps({'verifier_result': None if reward is None else {'rewards': {'reward': reward}},
                                   'exception_info': {'exception_type': exception} if exception else None}))
        (verifier / 'reward.txt').write_text(str(reward if written is None else written))
        (verifier / 'reward-details.json').write_text(json.dumps({'reward': reward if detailed is None else detailed,
                                                               'parse_status': parse}))
        return trial_evidence(path, root)

    base, oracle = trial('base', 0), trial('oracle', 1)
    assert verified_pair(base, oracle, files_unchanged=True)
    assert not verified_pair(base, oracle, files_unchanged=False)
    assert not verified_pair(base, trial('contradictory', 1, written=0), files_unchanged=True)
    assert not verified_pair(base, trial('details-mismatch', 1, detailed=0), files_unchanged=True)
    assert not verified_pair(base, trial('fallback', 1, parse='fallback'), files_unchanged=True)
    timed_out = trial('timeout', None, written=1, detailed=1, exception='VerifierTimeoutError')
    assert timed_out['written_reward'] == 1 and timed_out['reward'] is None
    assert not verified_pair(base, timed_out, files_unchanged=True)
    assert trial('rounded', 0.333333, detailed=1/3)['reward_consistent']
print('Assessment fixtures passed: scalar/details/file agreement, parser evidence and unchanged bytes required; written timeout reward never upgrades the trial.')
