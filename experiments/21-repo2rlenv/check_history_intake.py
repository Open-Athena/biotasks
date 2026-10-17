"""Exercise intake command boundaries with synthetic output and no subprocesses."""
import json
import os
import tarfile
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import run_history_intake_remote as runner
from repo2rlenv.spec.recipe_options import R2EGymOptions

config=json.loads(Path(__file__).with_name('biopython-history-broader-intake-config.json').read_text())
R2EGymOptions.model_validate(config['options'])
with tempfile.TemporaryDirectory() as temporary:
    root=Path(temporary); previous=Path.cwd();os.chdir(root)
    try:
        fixture=root/'fixture';fixture.mkdir();(fixture/'README').write_text('Synthetic runtime')
        with tarfile.open('repo2rlenv-source.tar.gz','w:gz') as archive:archive.add(fixture,arcname='runtime-fixture')
        for evaluate in [True,False]:
            current=dict(config)
            if evaluate:current['mode']='evaluate'
            Path('intake-config.json').write_text(json.dumps(current))
            out=root/('rejected' if evaluate else 'valid')
            calls=[]
            def subprocess_run(command,**kwargs):
                calls.append(command)
                if '-m' in command:
                    assert command[-3]=='repo2rlenv.pipelines.recipes.history.worker'
                    selected=Path(command[-1]);selected.mkdir(parents=True)
                    (selected/'generation.json').write_text(json.dumps({'candidates':[], 'attempted':1}))
                return SimpleNamespace(returncode=0)
            with patch.dict(os.environ,{'IRIS_OUTPUT_DIR':str(out)}), patch.object(runner.hashlib,'file_digest',return_value=SimpleNamespace(hexdigest=lambda:'7e387fbb04d5374964de37a31b63e6cabc310198703213c6a40bf8d5c6dd4755')),patch.object(runner.subprocess,'run',side_effect=subprocess_run):
                result=runner.main()
            if evaluate:
                assert result==1 and calls==[]
            else:
                assert result==0 and len(calls)==2
                status=json.loads((out/'status.json').read_text())
                assert status['model_calls']==status['test_executions']==status['candidate_generation_attempts']==0
    finally:os.chdir(previous)
print('PASS: native options validate, evaluate mode rejected before setup, selection-only command and zero model/test execution accounting')
