"""Stream the full native LCC build contexts into an unresolved Marin TaskSpec.

No builds or schema/runtime validation occur here. Keeping two independent build
contexts preserves the native learner/verifier distinction and all source bytes.
"""
import argparse
import base64
import hashlib
import json
import os
import tomllib
from pathlib import Path

MARIN_REVISION = '45a044387ccd95ab698b4a592056aadaff961540'


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(65536), b''):
            h.update(block)
    return h.hexdigest()


def resources(root):
    for path in sorted(root.rglob('*')):
        if path.is_symlink():
            raise ValueError('Linked input requires an explicit conversion policy')
        if path.is_file():
            if path.stat().st_size > 48 * 1024**2:
                raise ValueError('Input exceeds bounded single-resource allowance')
            yield path


def write_resources(stream, root, paths):
    stream.write('[')
    for index, path in enumerate(paths):
        if index:
            stream.write(',')
        resource = {'path': str(path.relative_to(root)),
                    'source': {'kind': 'inline_file', 'content_base64': base64.b64encode(path.read_bytes()).decode()},
                    'mode': format(path.stat().st_mode & 0o777, '04o')}
        json.dump(resource, stream)
    stream.write(']')


def prepare(task, output):
    config = tomllib.loads((task/'task.toml').read_text())
    if config['verifier']['environment_mode'] != 'separate':
        raise ValueError('Expected the native separate verifier')
    contract = json.loads((task/'tests/contract.json').read_text())
    artifacts = config['artifacts']
    if {x['source'] for x in artifacts} != {'/workspace/'+x for x in contract['submitted_files']}:
        raise ValueError('Submission and verifier contracts disagree')
    paths = list(resources(task))
    manifest = [{'path':str(p.relative_to(task)), 'bytes':p.stat().st_size,
                 'sha256':digest(p), 'mode':format(p.stat().st_mode & 0o777,'04o')} for p in paths]
    identity = hashlib.sha256(json.dumps(manifest,sort_keys=True).encode()).hexdigest()
    environment = {'capabilities':['shell','filesystem'],'command_semantics':'linux_process','working_directory':'/workspace'}
    spec = {'schema_version':'0.27','id':'repo2rlenv-swe-smith/'+identity,
            'source':{'dataset':'Open-Athena/biotasks-issue-21','revision':'sha256:'+identity,
                      'row':config['task']['name'],'importer_revision':'sha256:'+digest(Path(__file__))},
            'context':{'events':[{'type':'message','role':'user','content':(task/'instruction.md').read_text()}]},
            'answer_type':'workspace_state','answer_format':{'kind':'plain_text'},
            'output_paths':[x['source'] for x in artifacts],
            'tags':['biology','sequence-complexity','repo2rlenv','swe_smith','unvalidated']}
    grader = {'kind':'script','argv':['sh','/tests/test.sh'],'cwd':'/workspace','answer_path':None,
              'artifacts':[{'source':x['source'],'target':x['source'],'kind':'file','missing':'error'} for x in artifacts],
              'reward':{'kind':'file','files':[{'path':'/logs/verifier/reward.txt','format':'number'}]},
              'timeout':float(config['verifier']['timeout_sec'])}
    output.mkdir(parents=True,exist_ok=False)
    target = output/'task.json'
    with target.open('x') as f:
        f.write(json.dumps(spec)[:-1]+',"environment_requirements":')
        def write_environment(folder):
            f.write(json.dumps(environment)[:-1]+',"docker_build":{"files":')
            write_resources(f, task/folder, resources(task/folder))
            f.write('}}')
        write_environment('environment')
        f.write(',"resources":{"worker":[],"oracle":')
        write_resources(f,task/'solution',resources(task/'solution'))
        f.write(',"verifier":')
        write_resources(f,task/'tests',[p for p in resources(task/'tests') if p.parent==task/'tests' and p.name!='Dockerfile'])
        f.write('},"grader":'+json.dumps(grader)[:-1]+',"environment":')
        write_environment('tests')
        f.write('}}\n')
    report = {'stage':'prepared_unvalidated','task_id':spec['id'],'marin_revision':MARIN_REVISION,
              'native_asset_manifest':manifest,'task_json_sha256':digest(target),'task_json_bytes':target.stat().st_size,
              'native_reward':'binary all expected native tests pass; partial correctness remains zero',
              'learner_and_verifier_build_contexts_distinct':True,'submitted_files':contract['submitted_files'],
              'model_calls':0,'docker_build_executed':False,'marin_schema_validated':False,'runtime_parity':False,
              'limitations':['Full inline source contexts require remote schema validation and execution',
                             'Base image and package indexes remain rebuild dependencies',
                             'Network policy and resource limits must be enforced by the execution harness']}
    (output/'conversion.json').write_text(json.dumps(report,indent=2)+'\n')
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--task',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    report=prepare(args.task,args.output)
    print(json.dumps({k:report[k] for k in ['stage','task_id','task_json_bytes','task_json_sha256']}))
