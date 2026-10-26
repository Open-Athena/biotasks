"""Offline safety checks for the experiment-only dependency handoff."""
from datetime import datetime, timezone
from unittest.mock import patch
import resume_after_dependencies as handoff


def check(running, generation_done, cleanup_done, waiter=None, cleanup_waiter_alive=True):
    def completed(directory):
        return generation_done if directory.name == 'generation' else cleanup_done
    def read(path):
        return waiter if path.name == 'cleanup-wait-state.json' else [{'pid': 2 if path.name == 'cleanup-waiter-process.json' else 1, 'start_ticks': '1'}]
    def alive(record):
        return cleanup_waiter_alive if record[0]['pid'] == 2 else running
    with patch.object(handoff, 'PINS', {}), patch.object(handoff, 'process_alive', side_effect=alive), patch.object(handoff, 'complete', side_effect=completed), patch.object(handoff, 'read', side_effect=read):
        return handoff.assess()


fresh = {'original_control_run_id': 'biotasks-val-issue67b-nibabel-6cca5227b8e1', 'state': 'waiting_for_original_worker_headroom', 'observed_utc': datetime.now(timezone.utc).isoformat()}
assert check(True, False, False) == 'waiting_for_existing_dendropy_controller'
assert check(False, True, False, fresh) == 'waiting_for_existing_nibabel_cleanup'
assert check(False, True, True) == 'ready_for_original_cohort_resume'
for arguments in [
    (False, False, False, fresh),
    (False, True, False, {**fresh, 'original_control_run_id': 'different-run'}),
    (False, True, False, {**fresh, 'state': 'unknown_failure'}),
    (False, True, False, fresh, False),
]:
    try:
        check(*arguments)
    except AssertionError:
        pass
    else:
        raise AssertionError('Unsafe handoff was admitted')
print('Seven offline dependency safety checks passed; no jobs or model calls')
