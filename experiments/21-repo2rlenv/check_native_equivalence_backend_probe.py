"""Probe classification checks; never run Docker or call a model locally."""
import contextlib
import io
import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch
import probe_native_equivalence_backend as probe

with tempfile.TemporaryDirectory() as temporary:
    root=Path(temporary)
    for name,available,error in [('unavailable',False,None),('available',True,None),('missing',False,FileNotFoundError('fixture'))]:
        target=root/name
        with patch.dict(os.environ,{'IRIS_OUTPUT_DIR':str(target)}), \
             patch.object(probe.docker,'is_docker_available',return_value=available,side_effect=error), \
             patch.object(probe.equivalence_tests,'complete',side_effect=AssertionError('Model call')), \
             patch.object(probe.docker.DockerSandbox,'start',side_effect=AssertionError('Allocation')), \
             contextlib.redirect_stdout(io.StringIO()):
            probe.main()
        row=json.loads((target/'native-equivalence-backend.json').read_text())
        assert row['status']==('backend_available_generation_unexecuted' if available else 'native_controller_docker_unavailable')
        assert row['model_calls']==row['worker_allocations']==row['task_generation_attempts']==0
        assert row['availability_exception_type']==('FileNotFoundError' if error else None)
    with patch.dict(os.environ,{},clear=True):
        try:probe.main()
        except RuntimeError:pass
        else:raise AssertionError('Unscoped local runtime allowed')
print('PASS: unavailable/available/missing Docker classified; no model/container call; unscoped caller rejected.')
