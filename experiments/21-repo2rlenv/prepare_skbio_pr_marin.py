"""Prepare a portable PR2633 build context and a schema-unvalidated Marin mapping.

This preserves the native graded reward and original grading/reference bytes.
Preparation does not prove a Docker build, TaskSpec validation or runtime parity.
"""
import argparse
import base64
import hashlib
import json
import shutil
import tomllib

import tomli_w
from pathlib import Path

from prepare_skbio_pr_controls import offline_profile

MARIN_REVISION = '45a044387ccd95ab698b4a592056aadaff961540'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def files(root):
    result=[]
    for p in sorted(root.rglob('*')):
        if p.is_symlink():
            raise ValueError('Unexpected linked asset')
        if p.is_file():
            result.append({'path':str(p.relative_to(root)), 'sha256':digest(p.read_bytes()),
                           'mode':format(p.stat().st_mode & 0o777,'04o')})
    return result


def resource(path, relative):
    return {'path':str(relative),'source':{'kind':'inline_file','content_base64':base64.b64encode(path.read_bytes()).decode()},
            'mode':format(path.stat().st_mode & 0o777,'04o')}


def prepare(task, baseline, output):
    original=files(task)
    old=(task/'environment/Dockerfile').read_text()
    marker='FROM biotasks21-skbio-pr\n'
    base=baseline.read_text()
    if old.count(marker)!=1 or sum(x.startswith('FROM ') for x in base.splitlines())!=1:
        raise ValueError('Unexpected native or baseline image structure')
    portable=old.replace(marker,base.rstrip()+'\n',1)
    portable += '\n# Restore baseline native extensions for learner-side imports after git clean.\nRUN cp -a /opt/skbio-baseline-extensions/. /workspace/\n'
    output.mkdir(parents=True,exist_ok=False)
    bundle=output/'harbor-task'
    shutil.copytree(task,bundle)
    offline_profile(bundle)
    (bundle/'environment/Dockerfile').write_text(portable)
    config=tomllib.loads((bundle/'task.toml').read_text())
    metadata=config['metadata']['repo2env']
    metadata['original_reproducibility']=metadata.pop('reproducibility',{})
    metadata['validation_profile']='portable_offline_unvalidated'
    (bundle/'task.toml').write_text(tomli_w.dumps(config))
    # Exact bytes and modes for every grading, reference and instruction asset.
    retained={x['path']:x for x in original if x['path'] not in {'environment/Dockerfile','environment/docker-compose.yaml','task.toml'}}
    actual={x['path']:x for x in files(bundle) if x['path'] in retained}
    assert retained==actual
    manifest=files(bundle)
    identity=digest(json.dumps(manifest,sort_keys=True).encode())
    environment={'capabilities':['shell','filesystem'],'command_semantics':'linux_process',
                 'working_directory':'/workspace','docker_build':{'files':[resource(bundle/'environment/Dockerfile','Dockerfile')]}}
    spec={
        'schema_version':'0.27','id':'repo2rlenv-pr-runtime/'+identity,
        'source':{'dataset':'Open-Athena/biotasks-issue-21','revision':'sha256:'+identity,
                  'row':'scikit-bio/scikit-bio#2633','importer_revision':'sha256:'+digest(Path(__file__).read_bytes())},
        'context':{'events':[{'type':'message','role':'user','content':(bundle/'instruction.md').read_text()}]},
        'environment_requirements':environment,'answer_type':'workspace_state',
        'answer_format':{'kind':'plain_text'},'output_paths':['/workspace'],
        'resources':{'worker':[], 'oracle':[resource(p,p.relative_to(bundle/'solution')) for p in sorted((bundle/'solution').rglob('*')) if p.is_file()],
                     'verifier':[resource(p,p.relative_to(bundle/'tests')) for p in sorted((bundle/'tests').rglob('*')) if p.is_file()]},
        'grader':{'kind':'script','argv':['bash','/tests/test.sh'],'cwd':'/workspace','environment':environment,
                  'answer_path':None,'artifacts':[{'source':'/workspace','target':'/workspace','kind':'directory','missing':'error'}],
                  'reward':{'kind':'file','files':[{'path':'/logs/verifier/reward.txt','format':'number'}]},'timeout':300.0},
        'tags':['biology','numerical-stability','repo2rlenv','pr_runtime','unvalidated'],
    }
    (output/'task.json').write_text(json.dumps(spec,indent=2)+'\n')
    report={'stage':'prepared_unvalidated','marin_revision':MARIN_REVISION,'source_manifest':original,
            'portable_manifest':manifest,'portable_manifest_sha256':identity,'baseline_dockerfile_sha256':digest(baseline.read_bytes()),
            'change':'Inline the preserved baseline Dockerfile in place of the local FROM tag; use the explicit offline runtime profile; restore baseline compiled extensions after checkout cleanup for learner imports.',
            'native_reward':'f2p_rate * p2p_rate; strict resolved status is separate',
            'native_grading_reference_instruction_bytes_and_modes_preserved':True,
            'worker_resources':0,'oracle_resources':len(spec['resources']['oracle']),
            'verifier_resources':len(spec['resources']['verifier']),
            'docker_build_executed':False,'marin_schema_validated':False,'marin_runtime_parity':False,
            'limitations':['Package indexes and base-image tag must resolve during a fresh build.',
                          'Network policy and resource isolation must be enforced by the execution harness.',
                          'Prepared context still requires build validation and native/Marin reward comparisons.']}
    (output/'conversion.json').write_text(json.dumps(report,indent=2)+'\n')
    return spec,report


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--task',type=Path,required=True)
    parser.add_argument('--baseline',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    a=parser.parse_args()
    spec,report=prepare(a.task,a.baseline,a.output)
    print(json.dumps({'stage':report['stage'],'task_id':spec['id'],'oracle_resources':report['oracle_resources'],'verifier_resources':report['verifier_resources']}))
