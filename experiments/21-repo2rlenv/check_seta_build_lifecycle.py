"""Offline lifecycle fault injection: preserve evidence and clean up on failure."""
import hashlib
import json
import os
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import run_seta_build as controller

root = Path(__file__).resolve().parent
designs = root / 'evidence/seta-design-01/designs.json'
digest = hashlib.sha256(designs.read_bytes()).hexdigest()
for fail in (False, True):
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        events = []
        args = SimpleNamespace(campaign=base/'campaign', wheel=base/'runtime.whl',
            designs=designs, designs_sha256=digest,
            seeds=root/'seeds/seta-genomic-intervals/seeds.json',
            adaptation=root/'glm-generation-adaptation.json', worker_name='offline-fixture')
        def provision(spec, directory, ledger, reserve_usd):
            events.append('allocate')
            assert spec.cpus == 2 and spec.memory_mb == 4096 and spec.disk_gb == 10
            return SimpleNamespace(id='fixture'), directory/'fixture.json'
        def build():
            events.append('build')
            spec = json.loads((args.campaign/'input-private.json').read_text())
            assert spec['execution']['timeout_sec'] == 6600
            assert spec['llm']['fallback'] is None
            (args.campaign/'partial.txt').write_text('partial result')
            if fail:
                raise RuntimeError('Synthetic build failure')
        def recover(*a):
            events.append('recover')
        def stop(*a):
            events.append('stop')
        with patch.dict(os.environ, {'REPO2RLENV_MODEL_WORKER':'1',
                  'IRIS_OUTPUT_DIR':str(base/'capture'),
                  'BIOTASKS21_GLM_ENDPOINT':'https://example.invalid/v1'}), \
             patch.object(controller,'check_runtime_wheel',return_value='a'*64), \
             patch.object(controller,'provision_worker',side_effect=provision), \
             patch.object(controller.build_seta_designs,'main',side_effect=build), \
             patch.object(controller,'recover_remote',side_effect=recover), \
             patch.object(controller,'stop_worker',side_effect=stop), \
             patch.object(controller,'verify_deleted',return_value={'independently_confirmed':True}):
            try:
                controller.run(args)
            except RuntimeError:
                assert fail
            else:
                assert not fail
        assert events == ['allocate','build','recover','stop']
        result=json.loads((args.campaign/'controller-result.json').read_text())
        assert result['status'] == ('failed' if fail else 'completed')
        assert result['cleanup']['independently_confirmed']
        assert (base/'capture/after-cleanup/author-evidence.tar.gz').is_file()
print('PASS: success and failed-build evidence recovered before cleanup; final archive retained; no remote or model calls')
