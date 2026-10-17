"""Exercise controller failure cleanup and preserved receipts without remote calls."""
import json
import hashlib
import os
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch
import run_parent_evolution_build as controller

root = Path(__file__).resolve().parent
with tempfile.TemporaryDirectory() as temp:
    temp = Path(temp)
    args = SimpleNamespace(campaign=temp/'campaign', wheel=temp/'runtime.whl',
        parent=root/'seeds/pr2633-parent-v1/parent', manifest=root/'seeds/pr2633-parent-v1/manifest.json',
        adaptation=root/'glm-generation-adaptation.json', worker_name='fixture',
        designs=root/'evidence/parent-evolution-design-01/designs.json',
        designs_sha256=hashlib.sha256((root/'evidence/parent-evolution-design-01/designs.json').read_bytes()).hexdigest())
    worker = SimpleNamespace(id='fixture', client=Mock())
    missing = RuntimeError('fixture absent'); missing.status_code = 404
    worker.client.get.side_effect = missing
    receipt = temp/'receipt.json'
    with patch.dict(os.environ, {'REPO2RLENV_MODEL_WORKER':'1', 'IRIS_OUTPUT_DIR':str(temp/'capture'),
                                'BIOTASKS21_GLM_ENDPOINT':'https://example.invalid/v1'}), \
         patch.object(controller, 'check_runtime_wheel', return_value='fixture'), \
         patch.object(controller, 'provision_worker', return_value=(worker, receipt)), \
         patch.object(controller.build_parent_evolution, 'run', side_effect=TimeoutError('fixture timeout')), \
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
print('PASS: failure capture, cleanup after evidence failure and deletion conflict, independent absence check, and preserved controller result; zero remote calls.')
