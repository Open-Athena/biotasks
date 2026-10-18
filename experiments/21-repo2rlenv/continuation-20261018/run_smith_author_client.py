"""Inference-only CPU client: author issues from saved contrasts using free GLM."""
import hashlib
import json
import os
import subprocess
import tarfile
import time
from pathlib import Path

import httpx
from iris.client.client import iris_ctx
from iris.cluster.types import JobName

from capture_author_process import capture
from preserve_author_output import preserve


def require_glm_model(response):
    response.raise_for_status()
    data = response.json()
    if not any(item.get('id') == 'glm-5.3' for item in data.get('data', [])):
        raise ValueError('Approved GLM model not advertised')


def main():
    if os.environ.get('DAYTONA_API_KEY') or os.environ.get('REPO2RLENV_REMOTE_WORKER'):
        raise RuntimeError('Inference-only client must not carry target sandbox execution credentials')
    started = time.monotonic()
    output = Path(os.environ['IRIS_OUTPUT_DIR'])
    output.mkdir(parents=True, exist_ok=True)
    status = {'stage': 'allocated_free_CoreWeave_GLM_issue_authoring', 'repository_builds_executed': False, 'sandbox_provisioning': False, 'status': 'setup', 'preflight_generation_calls': 0}
    try:
        for name, expected in [('repo2rlenv-source.tar.gz', '7e387fbb04d5374964de37a31b63e6cabc310198703213c6a40bf8d5c6dd4755'), ('generation-evidence.tar.gz', os.environ['BIOTASKS21_GENERATION_SHA256'])]:
            with Path(name).open('rb') as stream:
                assert hashlib.file_digest(stream, 'sha256').hexdigest() == expected
        resolution = iris_ctx().client.resolver_for_job(JobName.from_string(os.environ['BIOTASKS21_GLM_RELAY_JOB'])).resolve('glm-5.3')
        if not resolution.endpoints:
            raise RuntimeError('Approved relay not registered')
        endpoint = resolution.endpoints[0].url.rstrip('/')
        if not endpoint.endswith('/v1'):
            endpoint += '/v1'
        with httpx.Client(timeout=30) as client:
            response = client.get(endpoint + '/models', headers={'Authorization': 'Bearer ' + os.environ['BIOTASKS21_GLM_KEY']})
            status['models_http_status'] = response.status_code
            require_glm_model(response)
        status['model_advertised'] = True
        with tarfile.open('repo2rlenv-source.tar.gz') as archive:
            archive.extractall('native-runtime', filter='data')
        roots = list(Path('native-runtime').iterdir())
        assert len(roots) == 1
        root = roots[0]
        env = dict(os.environ)
        env.pop('VIRTUAL_ENV', None)
        env.update(UV_PROJECT_ENVIRONMENT=str(root.resolve() / '.venv'), BIOTASKS21_GLM_ENDPOINT=endpoint)
        subprocess.run(['uv', 'sync', '--frozen', '--no-dev', '--extra', 'mutation', '--python', '3.12.3', '--project', str(root)], env=env, check=True, timeout=600)
        with tarfile.open('generation-evidence.tar.gz') as archive:
            archive.extractall('inputs', filter='data')
        generation = json.loads(Path('inputs/native/generation/generation.json').read_text())
        constraints = json.loads(Path('author-manifest.json').read_text())
        assert generation['attempted'] <= constraints['maximum_new_mutation_attempts']
        assert len(generation['candidates']) <= constraints['maximum_authoring_candidates'] <= 2
        assert not set(constraints['prior_candidate_ids']) & {x['id'] for x in generation['candidates']}
        remaining = int(6900 - (time.monotonic() - started))
        if remaining < 900:
            raise TimeoutError('Insufficient remaining authoring window')
        command = [str(root / '.venv/bin/python'), 'author_swe_smith_issues.py', '--generation', 'inputs/native/generation', '--output', 'author-output', '--adaptation', 'glm-generation-adaptation.json']
        status.update(status='authoring', candidate_count=len(generation['candidates']))
        (output / 'wrapper-status.json').write_text(json.dumps(status, indent=2) + '\n')
        code = capture(command, source=Path('author-output'), output=output / 'child', timeout=remaining, env=env, maximum_bytes=64 * 1024**2)
        status.update(status='completed' if code == 0 else 'failed', child_exit_code=code)
        return code
    except Exception as exc:
        status.update(status='preflight_setup_or_authoring_failed', error_type=type(exc).__name__)
        return 1
    finally:
        status['elapsed_seconds'] = round(time.monotonic() - started, 3)
        (output / 'wrapper-status.json').write_text(json.dumps(status, indent=2) + '\n')
        print('BIOTASKS21_AUTHOR_STATUS ' + json.dumps(status), flush=True)
        if Path('author-output').is_dir() and not (output / 'child/author-evidence.tar.gz').exists():
            preserve(Path('author-output'), output / 'wrapper-fallback', max_bytes=64 * 1024**2)


if __name__ == '__main__':
    raise SystemExit(main())
