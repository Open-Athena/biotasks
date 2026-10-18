"""Paired native/Marin correctness controls for the frozen portable PR profiles."""
import argparse
import asyncio
import base64
import hashlib
import json
import os
import shutil
import subprocess
from dataclasses import asdict
from pathlib import Path

from shellbox.backends.docker.machine import DockerMachineFactory
from shellbox.machine import Command, MachineSpec, NetworkPolicy, RegistryImage
from taskcompendium.models import ConversationTrace, GradingAttempt, TaskSpec, TextMessage, require_resolved_environment
from taskcompendium.runtime.grading import grade_in_sandbox

REGISTRY = 'biotasks21-pr-parity-registry'
PRIVATE_PATH_CHECK = 'test ! -e /tests && test ! -e /solution && test ! -e /oracle.patch'


def materialize(resources, root):
    root.mkdir(parents=True, exist_ok=False)
    for item in resources:
        relative = Path(item['path'])
        assert not relative.is_absolute() and '..' not in relative.parts
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(base64.b64decode(item['source']['content_base64'], validate=True))
        target.chmod(int(item['mode'], 8))


def run(argv, log, timeout=1800):
    with log.open('ab') as stream:
        result = subprocess.run(argv, stdout=stream, stderr=stream, timeout=timeout)
    result.check_returncode()


async def checked(machine, argv, timeout=120):
    result = await machine.run(Command(tuple(argv), timeout=timeout))
    assert result.exit_code == 0, {'command': argv[0], 'exit_code': result.exit_code}
    return result


class EvidenceMachine:
    """Read the grader's own detail file before normal runtime teardown."""

    def __init__(self, machine, output):
        self.machine = machine
        self.output = output
        self.details = None

    def __getattr__(self, name):
        return getattr(self.machine, name)

    async def close(self):
        try:
            result = await self.machine.run(Command(('cat', '/logs/verifier/reward-details.json'), timeout=30, output_limit_bytes=131072))
            if result.exit_code == 0 and not result.stdout_truncated:
                self.details = json.loads(result.stdout)
                self.output.write_text(json.dumps(self.details, indent=2) + '\n')
        finally:
            await self.machine.close()


class EvidenceFactory:
    """Delegate unchanged machine creation; retain grader details for comparison."""

    def __init__(self, factory, output):
        self.factory = factory
        self.output = output
        self.created = []

    def __getattr__(self, name):
        return getattr(self.factory, name)

    async def create(self, spec):
        assert not self.created, 'Expected exactly one Marin grader machine'
        machine = EvidenceMachine(await self.factory.create(spec), self.output)
        self.created.append(machine)
        return machine


async def controls(task, image, oracle, verifier, inputs, output):
    factory = DockerMachineFactory()
    spec = MachineSpec(RegistryImage(image), cpus=1, memory_mb=2048, network=NetworkPolicy.DENY)
    rows = []
    for case in inputs['cases']:
        name = case['case']
        row = {'case': name, 'expected_reward': case['expected_reward'], 'solution_sha256': case['solution_sha256']}
        rows.append(row)
        assert hashlib.sha256(case['solution_shell'].encode()).hexdigest() == case['solution_sha256']
        for route in ('native', 'marin'):
            learner = await factory.create(spec)
            try:
                await checked(learner, ['sh', '-c', PRIVATE_PATH_CHECK])
                row[route + '_initial_private_paths_absent'] = True
                probe = 'import numpy; import skbio' if inputs['pr'] in (2630, 2636) else 'import numpy; import Bio; from Bio.PDB.qcprot import QCPSuperimposer'
                await checked(learner, ['python', '-c', probe])
                row[route + '_initial_imports_passed'] = True
                if case.get('requires_reference_patch', name == 'native_reference'):
                    actor = output / (name + '-' + route + '-actor')
                    actor.mkdir()
                    shutil.copyfile(oracle / 'patch.diff', actor / 'patch.diff')
                    (actor / 'solve.sh').write_text(case['solution_shell'])
                    (actor / 'solve.sh').chmod(int(case['solution_mode'], 8))
                    await learner.upload(actor, '/tmp/candidate-solution')
                    await checked(learner, ['bash', '/tmp/candidate-solution/solve.sh'])
                    await checked(learner, ['rm', '-rf', '/tmp/candidate-solution'])
                else:
                    shell = output / (name + '-submission.sh')
                    shell.write_text(case['solution_shell'])
                    await learner.upload(shell, '/tmp/candidate.sh')
                    await checked(learner, ['bash', '/tmp/candidate.sh'])
                    await checked(learner, ['rm', '/tmp/candidate.sh'])
                if route == 'native':
                    if inputs.get('license_transport'):
                        normalized = await checked(learner, ['python', '-c', inputs['license_transport']['normalization_program']])
                        row['native_license_transport'] = json.loads(normalized.stdout)
                    await learner.upload(verifier, '/tests')
                    await checked(learner, ['mkdir', '-p', '/logs/verifier'])
                    result = await learner.run(Command(('bash', '/tests/test.sh'), timeout=300, output_limit_bytes=262144))
                    (output / (name + '-native.log')).write_bytes(result.stdout + result.stderr)
                    assert result.exit_code == 0
                    result = await checked(learner, ['cat', '/logs/verifier/reward-details.json'])
                    row['native_details'] = json.loads(result.stdout)
                    row['native_reward'] = row['native_details']['reward']
                else:
                    attempt = GradingAttempt(ConversationTrace(events=(*task.context.events, TextMessage(role='assistant', content='Done.'))))
                    observer = EvidenceFactory(factory, output / (name + '-Marin-reward-details.json'))
                    result = await grade_in_sandbox(task, attempt, observer, spec, task_machine=learner, timeout=300)
                    row['marin_result'] = asdict(result)
                    row['marin_reward'] = result.reward
                    assert result.status == 'graded' and len(observer.created) == 1
                    row['marin_details'] = observer.created[0].details
                    assert row['marin_details'] is not None, 'Grader detail evidence missing'
                    await checked(learner, ['sh', '-c', PRIVATE_PATH_CHECK])
                    row['marin_postgrade_private_paths_absent'] = True
                    if inputs.get('license_transport'):
                        materialized = await checked(learner, ['python', '-c', inputs['license_transport']['materialized_probe']])
                        row['marin_license_transport_verified'] = json.loads(materialized.stdout)
            finally:
                await learner.close()
                (output / 'controls.json').write_text(json.dumps(rows, indent=2) + '\n')
        assert row['native_reward'] == row['marin_reward'] == case['expected_reward']
        for key in ('parse_status', 'tests_parsed', 'f2p_total', 'p2p_total', 'f2p_passed', 'p2p_passed', 'reward', 'resolved', 'command_resolved'):
            assert row['native_details'][key] == row['marin_details'][key] == case['native_details'][key], {'case': name, 'field': key}
        assert row['native_details']['parse_status'] == 'ok'
        if case['expected_reward'] == 1:
            assert row['native_details']['resolved'] and row['native_details']['command_resolved']
            assert not row['native_details']['regressions'] and not row['native_details']['untracked_failed']
        row['passed'] = True
        (output / 'controls.json').write_text(json.dumps(rows, indent=2) + '\n')
    return rows


def main():
    if os.environ.get('REPO2RLENV_REMOTE_WORKER') != '1':
        raise RuntimeError('Authorized remote worker required')
    parser = argparse.ArgumentParser()
    parser.add_argument('--inputs', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    manifest = json.loads((args.inputs / 'manifest.json').read_text())
    records = []
    registry_log = args.output / 'registry.log'
    try:
        run(['docker', 'run', '-d', '--name', REGISTRY, '--memory', '128m', '--cpus', '0.25', '-p', '127.0.0.1:5000:5000', 'registry:2'], registry_log)
        for item in manifest['records']:
            pr = item['pr']
            record = {'pr': pr, 'stage': 'started', 'model_calls': 0}
            records.append(record)
            output = args.output / f'pr{pr}'
            output.mkdir()
            try:
                data = json.loads((args.inputs / item['task_spec']).read_text())
                task = TaskSpec.model_validate(data)
                assert not task.resources.worker and not task.resources.all
                assert task.resources.oracle and task.resources.verifier
                environment = data['environment_requirements']
                build, oracle, verifier = output / 'build', output / 'oracle', output / 'verifier'
                materialize(environment['docker_build']['files'], build)
                materialize(data['resources']['oracle'], oracle)
                materialize(data['resources']['verifier'], verifier)
                record['schema_validated'] = True
                tag = f'localhost:5000/biotasks21/pr{pr}:correctness-parity'
                run(['docker', 'build', '-t', tag, str(build)], output / 'docker.log')
                run(['docker', 'push', tag], output / 'docker.log')
                image = json.loads(subprocess.check_output(['docker', 'image', 'inspect', tag, '--format', '{{json .RepoDigests}}']))[0]
                environment.pop('docker_build')
                environment['docker_image'] = image
                data['grader']['environment'] = dict(environment)
                task = TaskSpec.model_validate(data)
                require_resolved_environment(task.environment_requirements)
                (output / 'resolved-task.json').write_text(task.model_dump_json(indent=2) + '\n')
                inputs = json.loads((args.inputs / item['control_inputs']).read_text())
                cases = asyncio.run(controls(task, image, oracle, verifier, inputs, output))
                record.update(stage='paired_native_Marin_controls_passed', image=image, cases=cases, pairs=len(cases), runtime_parity=True)
            except Exception as exc:
                record.update(stage='failed', error_type=type(exc).__name__, error=str(exc)[:500], runtime_parity=False)
            (args.output / 'summary.json').write_text(json.dumps({'stage': 'native_Marin_correctness_parity_not_Atlas_admission', 'marin_revision': manifest['marin_revision'], 'records': records, 'model_calls': 0, 'Atlas_admissions': 0}, indent=2) + '\n')
    finally:
        cleanup = subprocess.run(['docker', 'rm', '-f', REGISTRY], capture_output=True, timeout=60)
        (args.output / 'registry-cleanup.json').write_text(json.dumps({'returncode': cleanup.returncode}) + '\n')
    assert len(records) == len(manifest['records']) and all(x.get('runtime_parity') for x in records), 'Some paired controls failed'


if __name__ == '__main__':
    main()
