"""One recorded blind attempt after matching no-model provider controls."""
import json
import os
import subprocess
from pathlib import Path

from check_pr_provider_setup import main as prepare
from preserve_author_output import preserve


def resolve_endpoint():
    from iris.client.client import iris_ctx
    from iris.cluster.types import JobName

    job = os.environ['BIOTASKS21_GLM_RELAY_JOB']
    resolved = iris_ctx().client.resolver_for_job(JobName.from_string(job)).resolve('glm-5.3')
    if not resolved.endpoints:
        raise RuntimeError('Approved free GLM service unavailable')
    endpoint = resolved.endpoints[0].url.rstrip('/')
    return endpoint if endpoint.endswith('/v1') else endpoint + '/v1'


def main(*, provider='scaler_provider_environment'):
    if provider not in {'scaler_provider_environment', 'history_provider_environment',
                        'alpha_provider_environment'}:
        raise ValueError('Unreviewed blind provider')
    output = Path(os.environ['IRIS_OUTPUT_DIR'])
    output.mkdir(parents=True, exist_ok=True)
    state = {'stage': 'blind_solver_preparation', 'attempt_limit': 1}
    try:
        # Require evidence before dependency setup or endpoint discovery. The child
        # verifies accepted asset hashes, native rewards and matching task checksum.
        for name in ('baseline-result.json', 'reference-status.json', 'acceptance.json'):
            if not Path(name).is_file():
                raise FileNotFoundError('Missing required provider-control evidence')
        os.environ['BIOTASKS21_PROVIDER_MODULE'] = provider
        root, env = prepare()
        env.update(REPO2RLENV_MODEL_WORKER='1',
                   BIOTASKS21_PROVIDER_MODULE=provider,
                   BIOTASKS21_GLM_ENDPOINT=resolve_endpoint())
        command = [str(root / '.venv/bin/python'), 'run_pr_blind_solver.py',
                   '--baseline', 'baseline-result.json',
                   '--reference', 'reference-status.json', '--task', 'task',
                   '--acceptance', 'acceptance.json', '--output', 'solver-output']
        state['stage'] = 'blind_solver_child'
        with (output / 'solver-controller.log').open('w') as log:
            result = subprocess.run(command, env=env, stdout=log, stderr=log,
                                    timeout=1200)
        state['child_exit_code'] = result.returncode
        return result.returncode
    except Exception as exc:
        state.update(status='failed', error_type=type(exc).__name__)
        return 1
    finally:
        (output / 'wrapper-status.json').write_text(json.dumps(state, indent=2) + '\n')
        if Path('solver-output').is_dir():
            preserve(Path('solver-output'), output / 'wrapper-fallback')


if __name__ == '__main__':
    raise SystemExit(main())
