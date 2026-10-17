"""Exercise controller failure cleanup and preserved receipts without remote calls."""
import json
import hashlib
import os
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch
import run_swe_gen_controller as controller

root = Path(__file__).resolve().parent
with tempfile.TemporaryDirectory() as temp:
    temp = Path(temp)
    args = SimpleNamespace(campaign=temp/'campaign', wheel=temp/'runtime.whl',
        profile=root/'swe-gen-skbio-profile.json',
        adaptation=root/'glm-generation-adaptation.json', worker_name='fixture',
        source=root/'evidence/swe-gen-skbio-preparation/source.json',
        source_sha256=hashlib.sha256((root/'evidence/swe-gen-skbio-preparation/source.json').read_bytes()).hexdigest())
    worker = SimpleNamespace(id='fixture', client=Mock())
    missing = RuntimeError('fixture absent'); missing.status_code = 404
    worker.client.get.side_effect = missing
    receipt = temp/'receipt.json'
    with patch.dict(os.environ, {'REPO2RLENV_MODEL_WORKER':'1', 'IRIS_OUTPUT_DIR':str(temp/'capture'),
                                'BIOTASKS21_GLM_ENDPOINT':'https://example.invalid/v1'}), \
         patch.object(controller, 'check_runtime_wheel', return_value='fixture'), \
         patch.object(controller, 'provision_worker', return_value=(worker, receipt)), \
         patch.object(controller.run_swe_gen_recipe, 'run', side_effect=TimeoutError('fixture timeout')), \
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
    saved = json.loads((args.campaign/'input-private.json').read_text())
    spec = controller.GenerationInput.model_validate(saved)
    profile = json.loads(args.profile.read_text())
    settings = json.loads(args.adaptation.read_text())
    pipeline, options = controller.run_swe_gen_recipe.prepare(spec, profile, settings, args.source, args.source_sha256)
    url = profile['source']['urls'][0]
    cache = args.campaign/'runs'/spec.execution.run_id/'candidates'/hashlib.sha256(url.encode()).hexdigest()[:20]/'source.json'
    assert json.loads(cache.read_text()) == json.loads(args.source.read_text())
    assert pipeline.name == 'pr_to_env' and options.force_generate_instruction is False
    worker.client.get.side_effect = None
    assert not controller.verify_deleted(worker, timeout=0)['independently_confirmed']
    # Invalid frozen input must fail before a worker is allocated.
    args.campaign = temp/'invalid-campaign'
    args.source_sha256 = '0'*64
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
print('PASS: frozen source validated, changed source rejected before allocation, original failure preserved, cleanup and output capture checked; zero remote calls.')
