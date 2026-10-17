"""Synthetic serialization and role-boundary check; no build or schema claims."""
import base64
import json
import tempfile
from pathlib import Path
from prepare_lcc_marin import prepare

with tempfile.TemporaryDirectory() as temp:
    root=Path(temp);task=root/'task'
    for folder in ('environment','tests','solution'):(task/folder).mkdir(parents=True)
    (task/'instruction.md').write_text('Repair the fixture.')
    (task/'task.toml').write_text('artifacts = [{ source="/workspace/module.py" }]\n[task]\nname="fixture"\n[verifier]\nenvironment_mode="separate"\ntimeout_sec=120\n')
    (task/'environment/Dockerfile').write_text('FROM learner-fixture\n')
    (task/'tests/Dockerfile').write_text('FROM verifier-fixture\n')
    (task/'tests/contract.json').write_text(json.dumps({'submitted_files':['module.py']}))
    (task/'tests/test.sh').write_text('echo 1')
    (task/'solution/solve.sh').write_text('echo reference')
    report=prepare(task,root/'output')
    spec=json.loads((root/'output/task.json').read_text())
    assert not spec['resources']['worker']
    assert spec['grader']['artifacts']==[{'source':'/workspace/module.py','target':'/workspace/module.py','kind':'file','missing':'error'}]
    def decoded(resources):
        return {r['path']:base64.b64decode(r['source']['content_base64']) for r in resources}
    assert decoded(spec['environment_requirements']['docker_build']['files'])=={'Dockerfile':b'FROM learner-fixture\n'}
    assert decoded(spec['grader']['environment']['docker_build']['files'])['Dockerfile']==b'FROM verifier-fixture\n'
    assert decoded(spec['resources']['oracle'])=={'solve.sh':b'echo reference'}
    assert 'Dockerfile' not in decoded(spec['resources']['verifier'])
    assert report['runtime_parity'] is False
print('PASS: streamed JSON is valid; distinct build contexts, private roles and exact file-only artifact mapping preserved on synthetic fixture.')
