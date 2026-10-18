"""Reject pending/unreviewed tasks before dispatch; preserve single-child routing."""
import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch
import run_library_blind_remote as runner

original = Path.cwd()
with tempfile.TemporaryDirectory() as tmp:
    try:
        os.chdir(tmp)
        for identity, provider in runner.PROFILES.items():
            Path('acceptance.json').write_text(json.dumps({
                'status': 'accepted_for_bounded_pilot', 'source_bundle_hash': identity}))
            with patch.object(runner, 'run_blind', return_value=0) as child:
                assert runner.main() == 0
                child.assert_called_once_with(provider=provider)
        for status, identity in [('runtime_probe_only_acceptance_pending', next(iter(runner.PROFILES))),
                                 ('rejected_instruction_verifier_mismatch', next(iter(runner.PROFILES))),
                                 ('accepted_for_bounded_pilot', 'sha256:unreviewed')]:
            Path('acceptance.json').write_text(json.dumps({
                'status': status, 'source_bundle_hash': identity}))
            with patch.object(runner, 'run_blind') as child:
                try: runner.main()
                except ValueError: pass
                else: raise AssertionError('Unaccepted/unreviewed task dispatched')
                child.assert_not_called()
    finally:
        os.chdir(original)
print('PASS: reviewed library profiles route once; pending/rejected/unreviewed tasks stop before solver setup; no services.')
