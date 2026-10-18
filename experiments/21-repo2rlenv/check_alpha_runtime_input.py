"""Synthetic rejection checks for pending history runtime inputs."""
import hashlib
import json
import tempfile
from pathlib import Path
from alpha_runtime_input import check_task

with tempfile.TemporaryDirectory() as tmp:
    task = Path(tmp) / 'task'
    task.mkdir()
    (task/'task.toml').write_text('''[metadata.repo2env]
bundle_hash="sha256:05a0a0b6a946e78c51b8b6848e6056474fd67df3f639701aba37132cef79c042"
recipe="swe_smith"
repository="https://github.com/scikit-bio/scikit-bio"
[environment]
network_mode="no-network"
[agent]
network_mode="no-network"
[verifier]
network_mode="no-network"
environment_mode="separate"
''')
    (task/'tests').mkdir()
    (task/'tests/contract.json').write_text(json.dumps({'submitted_files':['skbio/diversity/alpha/_base.py'],'expected_passes':[str(i) for i in range(34)]}))
    asset = task/'example.txt'
    asset.write_text('unchanged')
    record = {'status':'runtime_probe_only_acceptance_pending',
              'source_bundle_hash':'sha256:05a0a0b6a946e78c51b8b6848e6056474fd67df3f639701aba37132cef79c042','reward':{'range':[0,1]},'assets':{}}
    for p in task.rglob('*'):
        if not p.is_file():continue
        record['assets'][str(p.relative_to(task))]={'sha256':hashlib.sha256(p.read_bytes()).hexdigest(), 'mode':p.stat().st_mode & 0o7777}
    review = Path(tmp)/'input-review.json'
    review.write_text(json.dumps(record))
    check_task(task,review)
    def rejected():
        try: check_task(task,review)
        except ValueError: return
        raise AssertionError('Changed inputs accepted')
    asset.write_text('changed');rejected();asset.write_text('unchanged')
    original_mode=asset.stat().st_mode & 0o7777
    asset.chmod(original_mode ^ 0o100);rejected();asset.chmod(original_mode)
    (task/'extra').write_text('extra');rejected();(task/'extra').unlink()
    (task/'linked').symlink_to(asset);rejected();(task/'linked').unlink()
    record['source_bundle_hash']='sha256:unreviewed';review.write_text(json.dumps(record));rejected()
    record['source_bundle_hash']='sha256:05a0a0b6a946e78c51b8b6848e6056474fd67df3f639701aba37132cef79c042'
    contract=task/'tests/contract.json';original=contract.read_text();changed=json.loads(original);changed['expected_passes']=[]
    contract.write_text(json.dumps(changed));record['assets']['tests/contract.json']['sha256']=hashlib.sha256(contract.read_bytes()).hexdigest();review.write_text(json.dumps(record));rejected()
    contract.write_text(original);record['assets']['tests/contract.json']['sha256']=hashlib.sha256(contract.read_bytes()).hexdigest()
    record['status']='accepted_for_bounded_pilot';review.write_text(json.dumps(record));rejected()
print('PASS: pending probe accepted; changed bytes/modes, extra files, links and false acceptance rejected')
