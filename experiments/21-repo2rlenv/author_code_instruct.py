"""Collect native-gated code-instruct candidates for separate CPU validation.

No bootstrap, task export, acceptance, or solver score is claimed by this stage.
The native validation call site records candidates as deferred, never passed.
"""

import argparse
import dataclasses
import json
import os
from pathlib import Path

from code_instruct_adapter import adapted_code_instruct, code_instruct
from code_instruct_glm import adapted_code_instruct_glm
from repo2rlenv.execution.lifecycle import save_record
from repo2rlenv.spec.input import GenerationInput, LLMSpec
from repo2rlenv.spec.options import CodeInstructOptions


class AuthoringCollector(code_instruct.CodeInstructPipeline):
    def __init__(self, generation_input, options, output):
        # This stage deliberately has no BootstrapResult. The methods that
        # require a built environment are replaced below and cannot export.
        self.input = generation_input
        self.options = options
        self.bootstrap = None
        self._progress_cb = None
        self._llm_cost_usd = 0.0
        self.output = output
        self.records = []
        self.pending_seed = None

    def _start_sandbox(self):
        return None

    def _task_test_filename(self, seed, parsed):
        self.pending_seed = dataclasses.asdict(seed)
        return super()._task_test_filename(seed, parsed)

    def _verify_task(self, sandbox, parsed, *, test_filename):
        if sandbox is not None or self.pending_seed is None:
            raise ValueError('Unexpected author-only validation state')
        self.records.append({
            'status': 'authored_native_gates_passed_validation_deferred',
            'seed': self.pending_seed,
            'test_filename': test_filename,
            **dataclasses.asdict(parsed),
        })
        save_record(self.output / 'candidates.json', {
            'stage': 'authoring_only', 'records': self.records,
            'native_validation_executed': False, 'exported_tasks': 0,
        })
        self.pending_seed = None
        return code_instruct._VerifyOutcome(reason='validation_deferred')

    def _build_task(self, *args, **kwargs):
        raise RuntimeError('Author-only collector must not export tasks')


def main():
    if os.environ.get('REPO2RLENV_MODEL_WORKER') != '1':
        raise RuntimeError('Approved remote model-client worker required')
    parser = argparse.ArgumentParser()
    parser.add_argument('--repo-url', required=True)
    parser.add_argument('--ref', required=True)
    parser.add_argument('--source-glob', required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--adaptation', type=Path, required=True)
    args = parser.parse_args()
    settings = json.loads(args.adaptation.read_text())
    args.output.mkdir(parents=True, exist_ok=False)
    model = LLMSpec(provider='openai', model='glm-5.3',
        endpoint=os.environ['BIOTASKS21_GLM_ENDPOINT'], api_key_env='BIOTASKS21_GLM_KEY',
        timeout_sec=settings['request_timeout_sec'], max_concurrent=1, fallback=None)
    generation_input = GenerationInput(
        repo={'url': args.repo_url, 'ref': args.ref, 'access': 'public'},
        pipeline={'name': 'code_instruct'}, llm=model,
        output={'destination': str(args.output), 'org': 'open-athena', 'dataset_name': 'biotasks'},
    )
    options = CodeInstructOptions(limit=3, seed=24, file_glob=args.source_glob)
    collector = AuthoringCollector(generation_input, options, args.output)
    save_record(args.output / 'settings.json', {
        'stage': 'authoring_only', 'repo_url': args.repo_url, 'revision': args.ref,
        'options': options.model_dump(mode='json'), 'adaptation': settings,
        'validation_deferred': True, 'exported_tasks': 0,
    })
    with adapted_code_instruct(args.output), adapted_code_instruct_glm(settings, args.output / 'models'):
        result = collector.run(args.output / 'native-run')
    save_record(args.output / 'summary.json', {
        'stage': 'authoring_only', 'seed_candidates_attempted': result.candidates,
        'authored_candidates': len(collector.records), 'native_emitted': result.emitted,
        'skip_reasons': result.skip_reasons, 'validation_executed': False,
        'note': 'validation_deferred is staging, not a failed execution result',
    })


if __name__ == '__main__':
    main()
