"""Exercise controller failure cleanup and preserved receipts without remote calls."""
import json
import hashlib
import os
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch
import run_history_controller as controller

root = Path(__file__).resolve().parent
profile_name = os.environ.get('BIOTASKS21_TEST_PROFILE', 'skbio')
assert profile_name in {'skbio', 'biopython'}
pulls_dir = 'history-profile-preparation' if profile_name == 'skbio' else 'history-biopython-preparation'
with tempfile.TemporaryDirectory() as temp:
    temp = Path(temp)
    args = SimpleNamespace(campaign=temp/'campaign', wheel=temp/'runtime.whl',
        profile=root/f'swe-next-{profile_name}-profile.json',
        adaptation=root/'glm-generation-adaptation.json', worker_name='fixture',
        pulls=root/'evidence'/pulls_dir/'pulls.json',
        pulls_sha256=hashlib.sha256((root/'evidence'/pulls_dir/'pulls.json').read_bytes()).hexdigest())
    worker = SimpleNamespace(id='fixture', client=Mock())
    missing = RuntimeError('fixture absent'); missing.status_code = 404
    worker.client.get.side_effect = missing
    receipt = temp/'receipt.json'
    with patch.dict(os.environ, {'REPO2RLENV_MODEL_WORKER':'1', 'IRIS_OUTPUT_DIR':str(temp/'capture'),
                                'BIOTASKS21_GLM_ENDPOINT':'https://example.invalid/v1'}), \
         patch.object(controller, 'check_runtime_wheel', return_value='fixture'), \
         patch.object(controller, 'provision_worker', return_value=(worker, receipt)), \
         patch.object(controller.run_history_recipe, 'run', side_effect=TimeoutError('fixture timeout')), \
         patch.object(controller, 'recover_remote', side_effect=RuntimeError('fixture capture failure')), \
         patch.object(controller, 'stop_worker', side_effect=RuntimeError('fixture deletion conflict')) as stop:
        try:
            controller.run(args)
        except TimeoutError:
            pass
        else:
            raise AssertionError('Lost original failure')
    state = json.loads((args.campaign/'controller-result.json').read_text())
    assert state['status']=='failed' and state['error_type']=='TimeoutError'
    assert not state['remote_evidence_recovered'] and state['cleanup']['independently_confirmed']
    stop.assert_called_once()
    assert (temp/'capture/after-cleanup/author-evidence.tar.gz').is_file()
    worker.client.get.side_effect = None
    assert not controller.verify_deleted(worker, timeout=0)['independently_confirmed']
    # Invalid frozen input must fail before a worker is allocated.
    args.campaign = temp/'invalid-campaign'
    args.pulls_sha256 = '0'*64
    with patch.dict(os.environ, {'REPO2RLENV_MODEL_WORKER':'1', 'IRIS_OUTPUT_DIR':str(temp/'invalid-capture'),
                                'BIOTASKS21_GLM_ENDPOINT':'https://example.invalid/v1'}), \
         patch.object(controller, 'check_runtime_wheel', return_value='fixture'), \
         patch.object(controller, 'provision_worker') as allocate:
        try:
            controller.run(args)
        except ValueError:
            pass
        else:
            raise AssertionError('Changed PR context accepted')
        allocate.assert_not_called()
    # R2E-Gym needs no PR cache and must preserve its native pipeline identity.
    args.profile = root/f'r2e-gym-{profile_name}-profile.json'
    args.campaign = temp/'gym-campaign'
    worker.client.get.side_effect = missing
    with patch.dict(os.environ, {'REPO2RLENV_MODEL_WORKER':'1', 'IRIS_OUTPUT_DIR':str(temp/'gym-capture'),
                                'BIOTASKS21_GLM_ENDPOINT':'https://example.invalid/v1'}), \
         patch.object(controller, 'check_runtime_wheel', return_value='fixture'), \
         patch.object(controller, 'provision_worker', return_value=(worker, receipt)), \
         patch.object(controller.run_history_recipe, 'run') as generate, \
         patch.object(controller, 'recover_remote'), \
         patch.object(controller, 'stop_worker') as stop:
        controller.run(args)
    saved=json.loads((args.campaign/'input-private.json').read_text())
    assert saved['pipeline']['name']=='commit_runtime' and saved['pipeline']['recipe']=='r2e_gym'
    assert json.loads((args.campaign/'controller-result.json').read_text())['status']=='completed'
    generate.assert_called_once();stop.assert_called_once()
print('PASS: both native profiles, pre-allocation rejection, failure cleanup, independent absence, preserved results; zero remote calls.')
