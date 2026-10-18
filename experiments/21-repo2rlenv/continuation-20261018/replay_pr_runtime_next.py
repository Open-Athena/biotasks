"""Replay frozen pure-Python panel PRs through the unchanged native route.

Target code runs only in the authorized remote Docker sandbox. Parent extension
restoration retains the earlier explicit profile intervention. Exports are not
independently accepted tasks and no model is invoked.
"""
import argparse
import dataclasses
import hashlib
import json
import os
import re
import shlex
import shutil
import subprocess
import time
from pathlib import Path
from unittest.mock import patch

from repo2rlenv.bootstrap.spec import BootstrapResult, LanguageHint
from repo2rlenv.execution.lifecycle import save_record
from repo2rlenv.github import PullRequestSummary
from repo2rlenv.pipelines import pr_runtime, pr_runtime_validate
from repo2rlenv.spec.input import GenerationInput
from repo2rlenv.spec.options import PRRuntimeOptions


def test_command_for(config):
    biopython = config['repository'] == 'biopython/biopython'
    prefix = 'Tests/' if biopython else 'skbio/'
    if any(not p.startswith(prefix) for p in config['test_paths']):
        raise ValueError('Unexpected repository test root')
    cache_name = 'biopython' if biopython else 'skbio'
    targets = ['./' + p.removeprefix('Tests/') for p in config['test_paths']] if biopython else config['test_paths']
    workdir = '/workspace/Tests' if biopython else '/workspace'
    return 'cp -a /opt/' + cache_name + '-baseline-extensions/. /workspace/ && cd ' + workdir + ' && python -m pytest -o addopts= -v --tb=short ' + ' '.join(shlex.quote(p) for p in targets)


def checked_profile(folder):
    folder = Path(folder)
    config = json.loads((folder / 'profile.json').read_text())
    if config['schema_version'] != 1 or config['repository'] not in ('scikit-bio/scikit-bio', 'biopython/biopython'):
        raise ValueError('Unexpected frozen repository/profile')
    for name, expected in config['input_files'].items():
        if Path(name).name != name or name not in ('pr.json', 'pr.diff', 'Dockerfile', 'issue.json'):
            raise ValueError('Unexpected input filename')
        raw = (folder / name).read_bytes()
        if len(raw) != expected['bytes'] or hashlib.sha256(raw).hexdigest() != expected['sha256']:
            raise ValueError('Frozen input changed')
    if not {'pr.json', 'pr.diff', 'Dockerfile'} <= config['input_files'].keys():
        raise ValueError('Missing frozen inputs')
    pr = PullRequestSummary(**json.loads((folder / 'pr.json').read_text()))
    if (pr.number, pr.base_sha, pr.head_sha) != (config['pr_number'], config['base_sha'], config['head_sha']):
        raise ValueError('Candidate identity mismatch')
    if not re.fullmatch(r'[a-z0-9-]+', config['image_tag']):
        raise ValueError('Invalid local image tag')
    if not all(re.fullmatch(r'[a-f0-9]{40}', value) for value in (pr.base_sha, pr.head_sha)):
        raise ValueError('Source revisions must be full hashes')
    if any(Path(name).suffix not in ('.py', '.md', '.rst') for name in pr.changed_files):
        raise ValueError('Parent compiled restoration requires a pure-Python patch')
    source, tests = pr_runtime.split_patch_and_test_patch((folder / 'pr.diff').read_text())
    paths = pr_runtime._files_in_patch(tests)
    if paths != config['test_paths'] or not paths or any(Path(p).is_absolute() or '..' in Path(p).parts or not p.endswith('.py') for p in paths):
        raise ValueError('Changed test paths differ from the frozen native split')
    test_command_for(config)
    options = PRRuntimeOptions.model_validate(config['native_options'])
    if options.skip_validation or options.limit != 1 or not options.require_fail_to_pass or options.validation_timeout_sec != 600:
        raise ValueError('Native validation bounds changed')
    if not config['restore_parent_compiled_extensions']:
        raise ValueError('Expected the declared parent-extension profile')
    if pr_runtime._linked_issue_number(pr.body) != config['linked_issue']:
        raise ValueError('Linked issue changed')
    if config['linked_issue'] is not None:
        issue = json.loads((folder / 'issue.json').read_text())
        if issue['number'] != config['linked_issue']:
            raise ValueError('Issue identity mismatch')
    return config, pr, options


def replay(folder, output):
    config, pr, options = checked_profile(folder)
    output.mkdir(parents=True, exist_ok=False)
    shutil.copytree(folder, output / 'frozen-inputs')
    started = time.monotonic()
    with (output / 'build.log').open('w') as log:
        subprocess.run(['docker', 'build', '--progress=plain', '-t', config['image_tag'], str(folder)], stdout=log, stderr=log, check=True, timeout=1800)
    digest = subprocess.check_output(['docker', 'image', 'inspect', config['image_tag'], '--format', '{{.Id}}'], text=True).strip()
    biopython = config['repository'] == 'biopython/biopython'
    cache_name = 'biopython' if biopython else 'skbio'
    for name in ('baseline-freeze.txt', cache_name + '-baseline-extension-sha256.txt'):
        raw = subprocess.check_output(['docker', 'run', '--rm', '--network', 'none', '--cpus', '1', '--memory', '128m', digest, 'cat', '/opt/' + name], timeout=30)
        (output / name).write_bytes(raw)
    license_bytes = subprocess.check_output(['docker', 'run', '--rm', '--network', 'none', '--cpus', '1', '--memory', '128m', digest, 'cat', '/workspace/LICENSE.rst' if biopython else '/workspace/LICENSE.txt'], timeout=30)
    (output / 'source-LICENSE.txt').write_bytes(license_bytes)
    test_command = test_command_for(config)
    bootstrap = BootstrapResult(image_digest=digest, image_tag=config['image_tag'], language=LanguageHint.PYTHON, repo=config['repository'], ref=pr.base_sha, rebuild_cmds=[], test_cmds=[test_command], smoke_passed=False, iterations=0, build_time_sec=time.monotonic()-started, llm_provider='none; explicit frozen Docker profile', dockerfile_reconstruction=(folder / 'Dockerfile').read_text())
    save_record(output / 'bootstrap.json', dataclasses.asdict(bootstrap))
    spec = GenerationInput.model_validate({'repo': {'url': 'https://github.com/' + config['repository'], 'ref': pr.head_sha}, 'pipeline': {'name': 'pr_runtime'}, 'output': {'destination': str(output / 'tasks'), 'org': 'open-athena', 'dataset_name': 'biotasks21-pr'}, 'auth': {'use_gh_cli': False}})
    pipeline = pr_runtime.PRRuntimePipeline(spec, options, bootstrap)
    save_record(output / 'recipe-options.json', options.model_dump(mode='json'))
    start_sandbox = pipeline._start_validation_sandbox

    def offline_sandbox():
        sandbox = start_sandbox()
        try:
            subprocess.run(['docker', 'network', 'disconnect', 'bridge', sandbox.container_id], check=True)
            subprocess.run(['docker', 'update', '--cpus', '1', '--memory', '2048m', '--memory-swap', '2048m', sandbox.container_id], check=True)
            return sandbox
        except BaseException:
            sandbox.cleanup()
            raise

    native_validate = pr_runtime_validate.validate_pr

    def validate(**kwargs):
        result = native_validate(**kwargs)
        save_record(output / 'validation.json', dataclasses.asdict(result))
        return result

    owner_name = tuple(config['repository'].split('/'))

    class FrozenProvider:
        def list_merged_prs(self, owner, name, **kwargs):
            assert (owner, name) == owner_name
            return [pr]

        def fetch_pr_diff(self, owner, name, number, **kwargs):
            assert (owner, name, number) == (*owner_name, pr.number)
            return (folder / 'pr.diff').read_text()

        def fetch_issue(self, owner, name, number, **kwargs):
            assert (owner, name, number) == (*owner_name, config['linked_issue'])
            issue = json.loads((folder / 'issue.json').read_text())
            return issue['title'], issue['body']

    save_record(output / 'candidate.json', dataclasses.asdict(pr))
    provider = FrozenProvider()
    (output / 'rendered-instruction.md').write_text(pr_runtime._build_instruction(pr, *owner_name, provider=provider))
    with patch.object(pr_runtime, 'provider_for', return_value=provider), patch.object(pipeline, '_start_validation_sandbox', new=offline_sandbox), patch.object(pr_runtime_validate, 'validate_pr', new=validate):
        result = dataclasses.asdict(pipeline.run(output / 'tasks'))
    result['out_dir'] = str(result['out_dir'])
    save_record(output / 'result.json', result)
    return result


def main():
    if os.environ.get('REPO2RLENV_REMOTE_WORKER') != '1':
        raise RuntimeError('Execute target code only in the authorized remote worker')
    parser = argparse.ArgumentParser()
    parser.add_argument('--inputs', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    manifest = json.loads((args.inputs / 'manifest.json').read_text())
    if not 1 <= len(manifest['candidates']) <= 3 or manifest['conservative_allowance_after_selection'] > 10:
        raise ValueError('Unexpected frozen cohort/cap')
    args.output.mkdir(parents=True, exist_ok=False)
    rows = []
    for item in manifest['candidates']:
        folder = args.inputs / f"pr{int(item['pr'])}"
        raw = (folder / 'profile.json').read_bytes()
        if hashlib.sha256(raw).hexdigest() != item['profile_sha256']:
            raise ValueError('Cohort profile changed')
        record = {'pr': item['pr'], 'status': 'started', 'model_calls': 0}
        rows.append(record)
        save_record(args.output / 'cohort-summary.json', {'stage': 'native_runtime_not_independent_admission', 'records': rows})
        try:
            result = replay(folder, args.output / f"pr{item['pr']}")
            record.update(status='completed', **{k: result[k] for k in ('candidates', 'emitted', 'skipped', 'skip_reasons')})
        except Exception as exc:
            record.update(status='failed', error_type=type(exc).__name__)
        save_record(args.output / 'cohort-summary.json', {'stage': 'native_runtime_not_independent_admission', 'records': rows})
    print('BIOTASKS21_PR_RUNTIME_SUMMARY ' + json.dumps({'stage': 'native_runtime_not_independent_admission', 'records': rows}), flush=True)


if __name__ == '__main__':
    main()
