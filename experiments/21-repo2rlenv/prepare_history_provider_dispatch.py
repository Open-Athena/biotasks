"""Freeze a history runtime probe after preserved independent controls pass."""
import argparse
import hashlib
import json
from pathlib import Path
from history_runtime_input import check_task
from package_provider_task import pack

CODE = ('history_runtime_input.py', 'history_provider_environment.py',
        'pr_provider_environment.py', 'run_pr_provider_preflight.py',
        'run_history_provider_preflight.py', 'package_provider_task.py',
        'preserve_author_output.py')


def prepare(task, controls, source, output):
    from repo2rlenv.emitter.bundle import inspect_bundle
    identity = inspect_bundle(task)
    if not identity['integrity_passed']:
        raise ValueError('Original native bundle changed')
    manifest = json.loads((controls/'bundles/manifest.json').read_text())
    if manifest['source_bundle_hash'] != identity['bundle_hash']:
        raise ValueError('Controls refer to another task')
    summary = json.loads((controls/'summary.json').read_text())
    records = summary['records']
    if not records or not all(r['passed'] and r['completed'] and r['exception_type'] is None for r in records):
        raise ValueError('Independent controls incomplete')
    rewards = {r['case']:r['reward'] for r in records}
    if rewards.get('baseline') != 0 or rewards.get('native_reference') != 1 or rewards.get('alternative_masked_division') != 1:
        raise ValueError('Required positive and negative controls missing')
    assets = {}
    total = 0
    for path in task.rglob('*'):
        if path.is_symlink():
            raise ValueError('Linked task asset')
        if path.is_file():
            total += path.stat().st_size
            with path.open('rb') as stream:
                digest = hashlib.file_digest(stream,'sha256').hexdigest()
            assets[path.relative_to(task).as_posix()]={'sha256':digest,'mode':path.stat().st_mode & 0o7777}
    if total > 384*1024**2:
        raise ValueError('Runtime task transfer bound exceeded')
    non_solution = {k:v['sha256'] for k,v in assets.items() if k != 'solution/solve.sh'}
    if non_solution != manifest['unchanged_assets']:
        raise ValueError('Control assets differ from runtime task')
    output.mkdir(parents=True,exist_ok=False)
    review = {'status':'runtime_probe_only_acceptance_pending', 'source_bundle_hash':identity['bundle_hash'],
              'reward':{'range':[0,1]},'assets':assets,'independent_controls':rewards,
              'control_summary_sha256':hashlib.sha256((controls/'summary.json').read_bytes()).hexdigest(),
              'limits':['No fresh provider runtime result yet','No final acceptance or blind solve']}
    (output/'input-review.json').write_text(json.dumps(review,indent=2)+'\n')
    check_task(task,output/'input-review.json')
    transfer = pack(task,output/'task-bundle.tar.gz')
    (output/'task-bundle-manifest.json').write_text(json.dumps(transfer,indent=2)+'\n')
    root = Path(__file__).resolve().parent
    for name in CODE:
        (output/name).write_bytes((root/name).read_bytes())
    (output/'glm_remote.py').write_bytes((root/'run_history_provider_remote.py').read_bytes())
    raw=source.read_bytes()
    if hashlib.sha256(raw).hexdigest()!='7e387fbb04d5374964de37a31b63e6cabc310198703213c6a40bf8d5c6dd4755':
        raise ValueError('Runtime source changed')
    (output/'repo2rlenv-source.tar.gz').write_bytes(raw)
    files={}
    for path in sorted(output.iterdir()):
        with path.open('rb') as stream:
            files[path.name]={'bytes':path.stat().st_size,'sha256':hashlib.file_digest(stream,'sha256').hexdigest()}
    result={'stage':'prepared_not_dispatched','source_bundle_hash':identity['bundle_hash'],
            'model_calls':0,'workers':0,'required_slots':3,'probe_seconds':1800,'cleanup_seconds':240,
            'task_uncompressed_bytes':total,'files':files}
    (output/'manifest.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('task','controls','source','output'):
        parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args()
    print(json.dumps(prepare(args.task,args.controls,args.source,args.output)))
