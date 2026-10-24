"""Observe upstream unchanged; stop new calls at the approved actual-cost threshold."""

import dataclasses
import functools
import gzip
import hashlib
import json
import os
from pathlib import Path
import runpy
import sys
import time
from decimal import Decimal

from provider_usage import charge, generation


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


class Recorder:
    def __init__(self, root):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.current_pr = None
        self.calls = 0
        self.validations = 0
        self.executions = 0
        self.actual_cost = Decimal('0')
        self.threshold = Decimal('5')
        self.cost_unknown = False
        self.secrets = [os.environ.get(k, '') for k in ['OPENROUTER_API_KEY', 'GH_TOKEN', 'GITHUB_TOKEN']]

    def text(self, value):
        result = json.dumps(value, default=str, ensure_ascii=True)
        for secret in self.secrets:
            if secret:
                result = result.replace(secret, '[REDACTED]')
        return result

    def event(self, event, **fields):
        with (self.root / 'events.jsonl').open('a') as handle:
            handle.write(self.text({'event': event, 'time': time.time(), **fields}) + '\n')

    def save(self, name, value, *, compressed=False):
        text = self.text(value)
        if compressed:
            with gzip.open(self.root / name, 'wt') as handle:
                handle.write(text + '\n')
        else:
            (self.root / name).write_text(text + '\n')

    def completion(self, original):
        @functools.wraps(original)
        def observe(*args, **kwargs):
            if self.cost_unknown or self.actual_cost >= self.threshold:
                self.event('budget_stop', actual_cost_usd=str(self.actual_cost),
                           cost_unknown=self.cost_unknown, threshold_usd=str(self.threshold))
                raise RuntimeError('Experiment actual-cost stop threshold or unavailable charge')
            self.calls += 1
            index = self.calls
            selected = {k: kwargs[k] for k in ['model', 'messages', 'max_tokens',
                        'max_completion_tokens', 'temperature', 'response_format'] if k in kwargs}
            self.save(f'request-{index:03d}.json.gz', selected, compressed=True)
            self.event('model_request', call=index, model=kwargs.get('model'),
                       max_tokens=kwargs.get('max_tokens'), temperature=kwargs.get('temperature'))
            try:
                response = original(*args, **kwargs)
            except BaseException as error:
                # A failed call may have reached a provider. Do not assume it was free.
                self.cost_unknown = True
                self.event('model_exception', call=index, exception_type=type(error).__name__)
                self.billing()
                raise
            usage = getattr(response, 'usage', None)
            if hasattr(usage, 'model_dump'):
                usage = usage.model_dump()
            elif usage is not None:
                usage = dict(usage)
            allowed = ['prompt_tokens', 'completion_tokens', 'total_tokens', 'cost',
                       'cost_details', 'prompt_tokens_details', 'completion_tokens_details']
            safe_usage = {k: usage[k] for k in allowed if k in (usage or {})}
            self.event('model_response', call=index, response_id=getattr(response, 'id', None),
                       model=getattr(response, 'model', None), usage=safe_usage)
            cost = charge(safe_usage.get('cost'))
            source = 'response.usage.cost'
            if cost is None:
                try:
                    metadata = generation(getattr(response, 'id', None))
                    self.save(f'generation-{index:03d}.json', metadata)
                    cost = charge(metadata.get('total_cost'))
                    source = 'generation.total_cost'
                except Exception as error:
                    self.event('billing_unavailable', call=index, exception_type=type(error).__name__)
            if cost is None:
                self.cost_unknown = True
            else:
                self.actual_cost += cost
            self.event('model_charge', call=index, actual_cost_usd=None if cost is None else str(cost),
                       source=source, cumulative_actual_usd=str(self.actual_cost))
            self.billing()
            # Return the exact object. Upstream continues computing its own estimate.
            return response
        return observe

    def billing(self):
        self.save('billing.json', {'model_calls': self.calls,
            'actual_cost_usd': str(self.actual_cost), 'cost_complete': not self.cost_unknown,
            'stop_threshold_usd': str(self.threshold), 'final_request_may_overshoot': True,
            'shared_account_deltas_used': False})


def install_hooks(recorder):
    import litellm
    from repo2rlenv import github
    from repo2rlenv.bootstrap.docker import DockerSandbox
    from repo2rlenv.pipelines.pr_runtime import PRRuntimePipeline
    from repo2rlenv.pipelines import pr_runtime_validate

    litellm.completion = recorder.completion(litellm.completion)
    original_list = github.list_merged_prs

    @functools.wraps(original_list)
    def listing(*args, **kwargs):
        values = original_list(*args, **kwargs)
        recorder.save('native-candidates.json', [dataclasses.asdict(v) for v in values])
        recorder.event('native_candidates_returned', count=len(values))
        return values
    github.list_merged_prs = listing

    original_filter = PRRuntimePipeline._pre_filter

    @functools.wraps(original_filter)
    def pre_filter(self, pr):
        recorder.current_pr = pr.number
        recorder.event('candidate_entered', pr=pr.number, base_sha=pr.base_sha, title=pr.title)
        return original_filter(self, pr)
    PRRuntimePipeline._pre_filter = pre_filter

    original_progress = PRRuntimePipeline._emit_progress

    @functools.wraps(original_progress)
    def progress(self, name, outcome, reason=''):
        recorder.event('native_decision', name=name, outcome=outcome, reason=reason)
        return original_progress(self, name, outcome, reason)
    PRRuntimePipeline._emit_progress = progress

    original_validate = pr_runtime_validate.validate_pr

    @functools.wraps(original_validate)
    def validate(*args, **kwargs):
        recorder.validations += 1
        index = recorder.validations
        recorder.event('validation_start', validation=index, pr=recorder.current_pr,
                       base_commit=kwargs.get('base_commit'), test_cmds=kwargs.get('test_cmds'),
                       language=kwargs.get('language'), timeout=kwargs.get('timeout'),
                       source_patch_sha256=digest(kwargs.get('patch', '')),
                       test_patch_sha256=digest(kwargs.get('test_patch', '')))
        try:
            value = original_validate(*args, **kwargs)
        except BaseException as error:
            recorder.event('validation_exception', validation=index, pr=recorder.current_pr,
                           exception_type=type(error).__name__, errno=getattr(error, 'errno', None))
            raise
        recorder.save(f'validation-{index:03d}-pr-{recorder.current_pr}.json.gz',
                      dataclasses.asdict(value), compressed=True)
        recorder.event('validation_end', validation=index, pr=recorder.current_pr,
                       status=value.status, f2p=len(value.fail_to_pass), p2p=len(value.pass_to_pass))
        return value
    pr_runtime_validate.validate_pr = validate

    original_exec = DockerSandbox.exec

    @functools.wraps(original_exec)
    def sandbox_exec(self, command, *args, **kwargs):
        recorder.executions += 1
        index = recorder.executions
        value = original_exec(self, command, *args, **kwargs)
        recorder.save(f'exec-{index:04d}-pr-{recorder.current_pr}.json.gz',
                      {'command': command, 'result': dataclasses.asdict(value)}, compressed=True)
        recorder.event('sandbox_exec_end', pr=recorder.current_pr, execution=index, command_sha256=digest(command),
                       exit_code=value.exit_code, duration_sec=value.duration_sec)
        return value
    DockerSandbox.exec = sandbox_exec


def main():
    recorder = Recorder('/work/native-observations')
    recorder.billing()
    install_hooks(recorder)
    executable = '/work/upstream/.venv/bin/repo2rlenv'
    sys.argv = [executable, *sys.argv[1:]]
    runpy.run_path(executable, run_name='__main__')


if __name__ == '__main__':
    main()
