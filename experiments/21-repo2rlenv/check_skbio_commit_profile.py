"""Reject altered commit inputs before allocation; no repository execution."""
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch
import replay_skbio_commit as replay
import run_smith_controls as controller

root=Path(__file__).resolve().parent
with tempfile.TemporaryDirectory() as tmp:
    directory=Path(tmp)
    for name in ('commit-71912.json','commit-71912.diff'):
        shutil.copy2(root/'evidence/skbio-commit-intake'/name,directory/name)
    original=(directory/'commit-71912.json').read_text()
    assert replay.check_inputs(directory)['sha']==replay.FIX
    for field,value in [('sha','wrong'),('parents',['wrong']),('files',[{'filename':'extension.c'}])]:
        record=json.loads(original);record[field]=value
        (directory/'commit-71912.json').write_text(json.dumps(record))
        try:replay.check_inputs(directory)
        except ValueError:pass
        else:raise AssertionError('Altered frozen input accepted')
    (directory/'commit-71912.json').write_text(original)
    with (directory/'commit-71912.diff').open('a') as stream:stream.write('changed')
    try:replay.check_inputs(directory)
    except ValueError:pass
    else:raise AssertionError('Changed diff accepted')
    with patch.object(sys,'argv',['check','--stage','skbio-commit','--campaign',str(directory/'campaign'),
                                 '--worker-name','fixture','--source-archive',str(directory/'missing')]), \
         patch.object(replay,'check_inputs',side_effect=ValueError('changed')), \
         patch.object(controller,'provision_worker') as allocate:
        try:controller.main()
        except ValueError:pass
        else:raise AssertionError('Changed input reached allocation')
        allocate.assert_not_called()
    with patch.dict(os.environ,{'REPO2RLENV_REMOTE_WORKER':'0'}),patch.object(replay.subprocess,'run') as run:
        try:replay.main()
        except RuntimeError:pass
        else:raise AssertionError('Local repository execution allowed')
        run.assert_not_called()
print('PASS: exact commit inputs accepted; wrong identity, parents, file scope and diff rejected before allocation; remote-only replay; no services.')

# Reproduce the remote missing-path failure using only flat transferred inputs.
import run_skbio_commit_remote as remote
with tempfile.TemporaryDirectory() as tmp:
    directory=Path(tmp)
    for name in remote.INPUT_SHA256:
        shutil.copy2(root/'evidence/skbio-commit-intake'/name,directory/name)
    target=remote.prepare_commit_inputs(directory)
    assert target == directory/'evidence/skbio-commit-intake'
    for name in remote.INPUT_SHA256:
        assert (target/name).read_bytes()==(directory/name).read_bytes()
    remote.prepare_commit_inputs(directory)  # identical reconstructed paths may be reused
    (target/'commit-71912.json').write_text('different')
    try:remote.prepare_commit_inputs(directory)
    except ValueError:pass
    else:raise AssertionError('Different nested controller input overwritten')
    assert (target/'commit-71912.json').read_text()=='different'
with tempfile.TemporaryDirectory() as tmp:
    directory=Path(tmp)
    shutil.copy2(root/'evidence/skbio-commit-intake/commit-71912.json',directory/'commit-71912.json')
    try:remote.prepare_commit_inputs(directory)
    except FileNotFoundError:pass
    else:raise AssertionError('Missing flat input accepted')
    assert not (directory/'evidence').exists()
    (directory/'commit-71912.diff').write_text('changed')
    try:remote.prepare_commit_inputs(directory)
    except ValueError:pass
    else:raise AssertionError('Changed flat diff accepted')
    assert not (directory/'evidence').exists()
    with patch.dict(os.environ,{'IRIS_OUTPUT_DIR':str(directory/'output')}), \
         patch.object(remote,'prepare_commit_inputs',side_effect=ValueError('changed')), \
         patch.object(remote.subprocess,'run') as run,patch.object(remote,'capture') as capture:
        assert remote.main()==1
        run.assert_not_called();capture.assert_not_called()
        assert json.loads((directory/'output/wrapper-failure.json').read_text())['error_type']=='ValueError'
print('PASS: flat inputs reconstructed exactly; missing/changed/conflicting inputs stop before setup or allocation.')
