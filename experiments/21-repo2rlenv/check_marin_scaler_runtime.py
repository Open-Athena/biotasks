"""Remote native/Marin parity for unchanged SCALER graders and fixed controls."""
import asyncio
import hashlib
import json
import os
import shutil
import subprocess
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
    records = []
    for case in cases:
        row = {'case': case['case'], 'expected_reward': case['expected_reward']}
        records.append(row)
        for route in ('native', 'marin'):
            learner = await factory.create(specs['learner'])
            try:
                await base.checked(learner, ['sh', '-c', 'test ! -e /tests && test ! -e /solution && python --version'])
                row[route + '_initial_private_paths_absent'] = True
                answer = base.ROOT / (case['case'] + '.txt')
                answer.write_text(case['answer'])
                await learner.upload(answer, '/workspace/answer.txt')
                if route == 'native':
                    verifier = await factory.create(specs['verifier'])
                    try:
                        submitted = base.ROOT / (case['case'] + '-submitted.txt')
                        await learner.download('/workspace/answer.txt', submitted)
                        assert submitted.read_bytes() == answer.read_bytes()
                        await verifier.upload(submitted, '/workspace/answer.txt')
                        execution = await verifier.run(Command(('sh', '/tests/test.sh'), timeout=60))
                        assert execution.exit_code == 0
                        reward = await base.checked(verifier, ['cat', '/logs/verifier/reward.txt'])
                        row['native_reward'] = float(reward.stdout)
                        await verifier.download('/logs/verifier', base.ROOT / 'native-logs' / case['case'])
                    finally:
                        await verifier.close()
                else:
                    attempt = GradingAttempt(ConversationTrace(events=(*task.context.events,
                        TextMessage(role='assistant', content='Done.'))))
                    result = await grade_in_sandbox(task, attempt, factory, specs['verifier'],
                                                   task_machine=learner, timeout=60)
                    row['marin_result'] = asdict(result)
                    row['marin_reward'] = result.reward
                    assert result.status == 'graded'
                await base.checked(learner, ['sh', '-c', 'test ! -e /tests && test ! -e /solution'])
                row[route + '_postgrade_private_paths_absent'] = True
            finally:
                await learner.close()
                (base.ROOT / 'controls.json').write_text(json.dumps(records, indent=2) + '\n')
        assert row['native_reward'] == row['marin_reward'] == case['expected_reward']
    return records


def main():
    if os.environ.get('REPO2RLENV_REMOTE_WORKER') != '1':
        raise RuntimeError('Remote execution required')
    root = base.ROOT
    root.mkdir(exist_ok=False)
    inputs = Path('/work/native/scaler-inputs')
    manifest = json.loads((inputs / 'manifest.json').read_text())
    results = []
    try:
        base.run(['docker', 'run', '-d', '--name', base.REGISTRY, '--memory', '128m',
                  '--cpus', '0.25', '-p', '127.0.0.1:5000:5000', 'registry:2'])
        for record in manifest['tasks']:
            base.ROOT = root / record['task']
            base.ROOT.mkdir()
            path = inputs / record['file']
            assert hashlib.sha256(path.read_bytes()).hexdigest() == record['sha256']
            data = json.loads(path.read_text())
            TaskSpec.model_validate(data)
            images = {}
            for role, environment in [('learner', data['environment_requirements']),
                                      ('verifier', data['grader']['environment'])]:
                build = base.ROOT / ('build-' + role)
                base.materialize(environment.pop('docker_build')['files'], build)
                tag = 'localhost:5000/biotasks21/' + record['task'] + ':' + role
                base.run(['docker', 'build', '-t', tag, str(build)], timeout=600)
                base.run(['docker', 'push', tag])
                images[role] = json.loads(base.run(['docker', 'image', 'inspect', tag,
                                                  '--format', '{{json .RepoDigests}}']))[0]
                environment['docker_image'] = images[role]
            task = TaskSpec.model_validate(data)
            (base.ROOT / 'resolved-task.json').write_text(task.model_dump_json(indent=2) + '\n')
            rows = asyncio.run(controls(task, images, record['cases']))
            bounds = all(x['marin_result'].get('score_min') == -1 and
                         x['marin_result'].get('score_max') == 1 for x in rows)
            results.append({'task_id': task.id, 'cases': rows, 'reward_values_match': True,
                            'native_reward_range': [-1, 1], 'score_range_metadata_matches': bounds})
            for role in ('learner', 'verifier'):
                shutil.rmtree(base.ROOT / ('build-' + role))
            (root / 'result.json').write_text(json.dumps({'status': 'reward_parity_completed',
                'tasks': results, 'model_calls': 0, 'acceptance': 'pending_score_metadata_review'}, indent=2) + '\n')
    finally:
        base.ROOT = root
        cleanup = subprocess.run(['docker', 'rm', '-f', base.REGISTRY], capture_output=True)
        (root / 'registry-cleanup.json').write_text(json.dumps({'returncode': cleanup.returncode}) + '\n')


if __name__ == '__main__':
    main()
