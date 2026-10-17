"""Exercise the real native input validator before the allocation boundary."""
import json
import os
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import run_endless_controller as controller

class Prepared(Exception):
    pass

seen = []
def prepare(spec, manifest, settings):
    seen.append(spec)
    assert spec.execution.run_id == 'endless-terminals-biological-build-01'
    assert spec.pipeline.recipe == 'endless_terminals'
    assert spec.llm.max_concurrent == 1 and spec.llm.fallback is None
    raise Prepared()

with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp)
    adaptation = root/'adaptation.json'
    adaptation.write_text('{}')
    args = SimpleNamespace(wheel=root/'fixture.whl', adaptation=adaptation,
        manifest=root/'manifest.json', campaign=root/'campaign', worker_name='fixture')
    with patch.dict(os.environ, {'REPO2RLENV_MODEL_WORKER':'1','IRIS_OUTPUT_DIR':str(root/'capture'),'BIOTASKS21_GLM_ENDPOINT':'https://example.invalid/v1'}), patch.object(controller,'check_runtime_wheel',return_value='fixture'), patch.object(controller.build_endless_biological,'prepare',side_effect=prepare), patch.object(controller,'provision_worker') as provision:
        try:
            controller.run(args)
        except Prepared:
            pass
        assert len(seen)==1
        provision.assert_not_called()
print(json.dumps({'stage':'real_native_input_validation_before_allocation','passed':True,'model_calls':0,'workers':0}))
