"""Remote native/Marin parity for the portable PR2633 numerical-stability task."""
import importlib.util
import json
from dataclasses import asdict
from pathlib import Path

import check_marin_runtime as base
from shellbox.backends.docker.machine import DockerMachineFactory
from shellbox.machine import Command, MachineSpec, NetworkPolicy, RegistryImage
from taskcompendium.models import ConversationTrace, GradingAttempt, TextMessage
from taskcompendium.runtime.grading import grade_in_sandbox


async def controls(task, image, oracle, verifier):
    inputs=json.loads(Path('/work/native/parity-controls.json').read_text())
    loader=importlib.util.spec_from_file_location('native_pr_verifier',verifier/'verifier.py')
    native=importlib.util.module_from_spec(loader)
    loader.loader.exec_module(native)
    f2p=json.loads((verifier/'f2p.json').read_text())
    p2p=json.loads((verifier/'p2p.json').read_text())
    factory=DockerMachineFactory()
    machine_spec=MachineSpec(RegistryImage(image),cpus=1,memory_mb=2048,network=NetworkPolicy.DENY)
    records=[]
    for case in inputs['cases']:
        row={'case':case['case'],'expected_reward':case['expected_reward']}
        records.append(row)
        for route in ('native','marin'):
            learner=await factory.create(machine_spec)
            try:
                await base.checked(learner,['sh','-c','test ! -e /tests && test ! -e /solution && test ! -e /oracle.patch'])
                row[route+'_learner_private_paths_absent']=True
                readiness=await base.checked(learner,['python','-c',
                    'import json,skbio,numpy,scipy,pandas; from skbio.stats.composition import ancombc2; '
                    'print(json.dumps({m.__name__:m.__version__ for m in [skbio,numpy,scipy,pandas]}))'])
                row[route+'_initial_imports']=json.loads(readiness.stdout)
                if case['case']=='native_reference':
                    await learner.upload(oracle/'patch.diff','/tmp/candidate.patch')
                    await base.checked(learner,['git','apply','/tmp/candidate.patch'])
                    await base.checked(learner,['rm','/tmp/candidate.patch'])
                else:
                    submission=base.ROOT/(case['case']+'-submission.sh')
                    submission.write_text(case['solution_shell'])
                    await learner.upload(submission,'/tmp/candidate.sh')
                    await base.checked(learner,['bash','/tmp/candidate.sh'])
                    await base.checked(learner,['rm','/tmp/candidate.sh'])
                if route=='native':
                    await learner.upload(verifier,'/tests')
                    await base.checked(learner,['mkdir','-p','/logs/verifier'])
                    result=await learner.run(Command(('bash','/tests/test.sh'),timeout=300))
                    (base.ROOT/(case['case']+'-native.log')).write_bytes(result.stdout+result.stderr)
                    row['native_exit_code']=result.exit_code
                    details=await base.checked(learner,['cat','/logs/verifier/reward-details.json'])
                    row['native_details']=json.loads(details.stdout)
                    row['native_reward']=row['native_details']['reward']
                    assert row['native_details']['parse_status']=='ok'
                else:
                    attempt=GradingAttempt(ConversationTrace(events=(*task.context.events,TextMessage(role='assistant',content='Done.'))))
                    result=await grade_in_sandbox(task,attempt,factory,machine_spec,task_machine=learner,timeout=300)
                    row['marin_result']=asdict(result)
                    row['marin_reward']=result.reward
                    assert result.status=='graded', row
                    assert not result.diagnostics['stdout_truncated']
                    parsed=native.parse_pytest(result.diagnostics['stdout'])
                    row['marin_test_counts']={'tests_parsed':len(parsed),
                        'f2p_passed':sum(parsed.get(x)=='PASSED' for x in f2p),
                        'p2p_passed':sum(parsed.get(x)=='PASSED' for x in p2p)}
                    await base.checked(learner,['sh','-c','test ! -e /tests && test ! -e /solution && test ! -e /oracle.patch'])
                    row['marin_postgrade_private_paths_absent']=True
            finally:
                await learner.close()
                (base.ROOT/'controls.json').write_text(json.dumps(records,indent=2)+'\n')
        assert row['native_exit_code']==0
        assert row['native_reward']==row['marin_reward']==case['expected_reward'],row
        for key in ('tests_parsed','f2p_passed','p2p_passed'):
            assert row['native_details'][key]==row['marin_test_counts'][key],row
        assert row['native_details']['tests_parsed']==len(f2p)+len(p2p)
    (base.ROOT/'result.json').write_text(json.dumps({'status':'native_marin_runtime_parity_controls_passed',
        'cases':records,'reward_semantics':'native_f2p_rate_times_p2p_rate',
        'model_calls':0,'blind_solver_attempts':0,'image':image,
        'limitations':'Fixed six-control suite; public image publication and final acceptance remain separate.'},indent=2)+'\n')


if __name__=='__main__':
    base.TAG='localhost:5000/biotasks21/pr2633:portable'
    base.controls=controls
    base.main()
