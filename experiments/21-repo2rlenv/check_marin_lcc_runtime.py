"""Remote six-case parity using LCC's separate native verifier image.

Runs on the pinned Marin environment. No solver/model calls; private assets are
never installed in the learner. Original native grader bytes remain unchanged.
"""
import asyncio
import base64
import hashlib
import json
import os
import subprocess
import shutil
from dataclasses import asdict
from pathlib import Path

import check_marin_runtime as base
from shellbox.backends.docker.machine import DockerMachineFactory
from shellbox.machine import Command, MachineSpec, NetworkPolicy, RegistryImage
from taskcompendium.models import ConversationTrace, GradingAttempt, TaskSpec, TextMessage
from taskcompendium.runtime.grading import grade_in_sandbox


async def controls(task, images, cases):
    factory = DockerMachineFactory()
    specs = {role: MachineSpec(RegistryImage(image), cpus=1, memory_mb=1024,
                              network=NetworkPolicy.DENY) for role, image in images.items()}
    contract_resource = next(r for r in task.resources.verifier if r.path=='contract.json')
    expected = set(json.loads(base64.b64decode(contract_resource.source.content_base64))['expected_passes'])
    records = []
    for case in cases:
        row = {'case':case['case'],'expected_reward':case['expected_reward']}
        records.append(row)
        for route in ('native','marin'):
            learner = await factory.create(specs['learner'])
            try:
                await base.checked(learner,['sh','-c','test ! -e /tests && test ! -e /solution'])
                row[route+'_initial_private_paths_absent'] = True
                readiness = await base.checked(learner,['python','-c','import Bio; from Bio.SeqUtils.lcc import lcc_mult; print(Bio.__version__)'])
                row[route+'_initial_import'] = readiness.stdout.decode().strip()
                if case.get('source_file'):
                    path = Path('/work/native/lcc-cases')/case['source_file']
                    assert hashlib.sha256(path.read_bytes()).hexdigest()==case['sha256']
                    await learner.upload(path,'/workspace/Bio/SeqUtils/lcc.py')
                if route=='native':
                    verifier = await factory.create(specs['verifier'])
                    try:
                        staging = base.ROOT/'submissions'/case['case']
                        for artifact in task.grader.artifacts:
                            target = staging/artifact.source.lstrip('/')
                            target.parent.mkdir(parents=True,exist_ok=True)
                            await learner.download(artifact.source,target)
                            await verifier.upload(target,artifact.target)
                        result = await verifier.run(Command(('sh','/tests/test.sh'),timeout=120))
                        assert result.exit_code==0
                        grade = await base.checked(verifier,['cat','/logs/verifier/result.json'])
                        row['native_details']=json.loads(grade.stdout)
                        assert set(row['native_details']['statuses'])==expected, 'Native test collection changed'
                        reward = await base.checked(verifier,['cat','/logs/verifier/reward.txt'])
                        row['native_reward']=float(reward.stdout)
                        await verifier.download('/logs/verifier',base.ROOT/'native-logs'/case['case'])
                    finally:
                        await verifier.close()
                else:
                    attempt=GradingAttempt(ConversationTrace(events=(*task.context.events,TextMessage(role='assistant',content='Done.'))))
                    result=await grade_in_sandbox(task,attempt,factory,specs['learner'],task_machine=learner,timeout=120)
                    row['marin_result']=asdict(result)
                    row['marin_reward']=result.reward
                    assert result.status=='graded'
                await base.checked(learner,['sh','-c','test ! -e /tests && test ! -e /solution'])
                row[route+'_postgrade_private_paths_absent']=True
            finally:
                await learner.close()
                (base.ROOT/'controls.json').write_text(json.dumps(records,indent=2)+'\n')
        assert row['native_reward']==row['marin_reward']==case['expected_reward'],row
    (base.ROOT/'result.json').write_text(json.dumps({'status':'native_marin_lcc_parity_passed',
        'cases':records,'reward_semantics':'native_binary_all_expected_tests_pass',
        'model_calls':0,'blind_solver_attempts':0,'images':images,
        'limitations':'Six fixed controls; counts preserved for native route only, no claim of exhaustive correctness.'},indent=2)+'\n')


def main():
    if os.environ.get('REPO2RLENV_REMOTE_WORKER')!='1':
        raise RuntimeError('Remote worker required')
    base.ROOT.mkdir()
    path=Path('/work/native/task.json')
    h=hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(65536),b''):h.update(block)
    summary=json.loads(Path('/work/native/conversion-summary.json').read_text())
    assert h.hexdigest()==summary['task_json_sha256']
    data=json.loads(path.read_text())
    TaskSpec.model_validate(data)
    contexts={'learner':data['environment_requirements'],'verifier':data['grader']['environment']}
    images={}
    try:
        base.run(['docker','run','-d','--name',base.REGISTRY,'--memory','128m','--cpus','0.25','-p','127.0.0.1:5000:5000','registry:2'])
        for role, environment in contexts.items():
            build=base.ROOT/('build-'+role)
            base.materialize(environment.pop('docker_build')['files'],build)
            tag='localhost:5000/biotasks21/lcc:'+role
            base.run(['docker','build','-t',tag,str(build)],timeout=1800)
            base.run(['docker','push',tag])
            images[role]=json.loads(base.run(['docker','image','inspect',tag,'--format','{{json .RepoDigests}}']))[0]
            environment['docker_image']=images[role]
        task=TaskSpec.model_validate(data)
        (base.ROOT/'resolved-task.json').write_text(task.model_dump_json(indent=2)+'\n')
        cases=json.loads(Path('/work/native/lcc-cases/manifest.json').read_text())['cases']
        asyncio.run(controls(task,images,cases))
    finally:
        # Exact original contexts remain in the hashed input artifact. Avoid
        # archiving hundreds of MB of duplicate disposable materialization.
        for role in ('learner','verifier'):
            shutil.rmtree(base.ROOT/('build-'+role),ignore_errors=True)
        result=subprocess.run(['docker','rm','-f',base.REGISTRY],capture_output=True)
        (base.ROOT/'registry-cleanup.json').write_text(json.dumps({'returncode':result.returncode})+'\n')


if __name__=='__main__':
    main()
