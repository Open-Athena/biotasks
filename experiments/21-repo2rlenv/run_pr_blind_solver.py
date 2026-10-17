"""One blind GLM attempt on the accepted task after recorded provider controls."""
import argparse
import asyncio
import hashlib
import json
import os
from importlib.metadata import version
from pathlib import Path

from harbor.trial.trial import Trial
from harbor.models.task.task import Task
from glm_solver_settings import ATTEMPT_TIMEOUT_SEC, MODEL, agent_kwargs
from preserve_author_output import preserve
from run_pr_provider_preflight import check_task, cleanup, config


def check_controls(baseline, reference):
    base = json.loads(baseline.read_text())
    ref = json.loads(reference.read_text())
    assert base['exception_info'] is None
    assert base['verifier_result']['rewards']['reward'] == 0
    assert ref['status'] == 'passed' and ref['model_calls'] == 0
    cases = [x for x in ref['cases'] if x['agent'] == 'oracle']
    assert len(cases) == 1
    result = cases[0]['result']
    assert result['exception_info'] is None
    assert result['verifier_result']['rewards']['reward'] == 1
    assert result['task_checksum'] == base['task_checksum']
    return base['task_checksum']


def solver_config(task, output, endpoint):
    spec = config(task, output, 'terminus-2')
    spec.trial_name = 'glm-blind-01'
    spec.agent.model_name = MODEL
    spec.agent.kwargs = agent_kwargs(endpoint)
    spec.agent.override_timeout_sec = ATTEMPT_TIMEOUT_SEC
    return spec


async def run(args):
    assert os.environ.get('REPO2RLENV_MODEL_WORKER') == '1'
    assert version('harbor') == '0.22.0'
    check_task(args.task, args.acceptance)
    expected_checksum = check_controls(args.baseline, args.reference)
    assert Task(args.task).checksum == expected_checksum, 'Provider-control task changed'
    endpoint = os.environ['BIOTASKS21_GLM_ENDPOINT']
    assert os.environ.get('BIOTASKS21_GLM_KEY')
    os.environ['OPENAI_API_KEY'] = os.environ['BIOTASKS21_GLM_KEY']
    args.output.mkdir(parents=True, exist_ok=False)
    os.environ['BIOTASKS21_PROVIDER_RECEIPTS'] = str((args.output/'provider.jsonl').resolve())
    state = {'stage': 'blind_solver', 'attempts': 1, 'status': 'started',
             'task_checksum': expected_checksum,
             'control_sha256': {name: hashlib.sha256(path.read_bytes()).hexdigest()
                               for name, path in [('baseline', args.baseline), ('reference', args.reference)]}}
    try:
        trial = await Trial.create(solver_config(args.task, args.output, endpoint))
        result = await asyncio.wait_for(trial.run(), timeout=ATTEMPT_TIMEOUT_SEC)
        assert result.task_checksum == expected_checksum, 'Provider-control task changed'
        state['result'] = result.model_dump(mode='json')
        state['status'] = 'completed' if result.exception_info is None else 'trial_failed'
    except BaseException as exc:
        state.update(status='incomplete', error_type=type(exc).__name__)
        raise
    finally:
        try:
            cleanup(args.output)
        finally:
            (args.output/'solver-status.json').write_text(json.dumps(state, indent=2)+'\n')
            # Archive stays private until routing/credential eligibility review.
            preserve(args.output, Path(os.environ['IRIS_OUTPUT_DIR']))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    for name in ('task', 'acceptance', 'baseline', 'reference', 'output'):
        parser.add_argument('--'+name, type=Path, required=True)
    asyncio.run(run(parser.parse_args()))
