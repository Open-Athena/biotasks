"""Exercise control classification without executing repositories or providers."""
import json
import os
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch
import run_qcp_independent as runner
import prepare_qcp_controls as preparation
import prepare_skbio_pr_controls as assets
import repo2rlenv.emitter.bundle as bundle

cases = [('baseline',0),('native_reference',1),('alternative_svd',1),
         ('wrong_translation',0),('wrong_identity_rotation',0),('wrong_zero_reported_rms',0)]

def fake_prepare(task, output, **kwargs):
    output.mkdir()
    records = [{'case':name,'bundle':str(task),'expected_reward':reward,
                'interpretation':'coverage observation only' if reward is None else 'correctness control'}
               for name,reward in cases]
    (output/'manifest.json').write_text(json.dumps({'cases':records,'unchanged_assets':{}}))

with tempfile.TemporaryDirectory() as temp:
    root=Path(temp)
    for final_reward in (0,1):
        output=root/str(final_reward)
        process=Mock();process.wait.return_value=0;process.poll.return_value=0
        rewards=[0,1,1,0,0,final_reward]
        evidence=[SimpleNamespace(completed=True,reward=x,exception_type=None) for x in rewards]
        with patch.dict(os.environ, {'REPO2RLENV_REMOTE_WORKER':'1'}), \
             patch.object(sys,'argv',['check','--task',str(root/'task'),'--output',str(output)]), \
             patch.object(bundle,'inspect_bundle',return_value={'integrity_passed':True,'bundle_hash':'fixture'}), \
             patch.object(preparation,'prepare',side_effect=fake_prepare), \
             patch.object(assets,'retained_hashes',return_value={}), \
             patch.object(runner.subprocess,'Popen',return_value=process) as spawn, \
             patch.object(runner,'read_trial',side_effect=evidence):
            try:runner.main()
            except RuntimeError:
                assert final_reward==1
            else:assert final_reward==0
        rows=json.loads((output/'summary.json').read_text())['records']
        assert len(rows)==6 and rows[3]['passed']
        assert rows[-1]['expected_reward']==0 and rows[-1]['passed']==(final_reward==0)
        assert spawn.call_count==6
print('PASS: six controls, alternative-correct and incorrect variants, binary rejection and failure propagation; no workers/model calls.')
