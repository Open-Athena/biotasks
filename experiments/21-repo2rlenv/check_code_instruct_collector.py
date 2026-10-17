"""Verify the author-stage boundary with synthetic inputs and no model calls."""

import argparse
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from author_code_instruct import AuthoringCollector
from code_instruct_adapter import adapted_code_instruct, code_instruct
from repo2rlenv.execution.lifecycle import save_record
from repo2rlenv.pipelines._oss_instruct import ParsedTask, Seed
from repo2rlenv.spec.options import CodeInstructOptions


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)

    def clone(url, ref, token, destination, depth):
        (destination / 'Bio').mkdir(parents=True)
        (destination / 'Bio/__init__.py').write_text('')

    collector = AuthoringCollector(SimpleNamespace(auth=None, repo=SimpleNamespace(
        access='public', owner_name=('biopython', 'biopython'), url='unused', ref='unused')),
        CodeInstructOptions(limit=3), args.output)
    candidate = ParsedTask('Synthetic fixture', 'fixture test', 'fixture solution')
    with (
        adapted_code_instruct(args.output),
        patch.object(code_instruct, 'resolve_repo_token', return_value=None),
        patch.object(code_instruct, '_shallow_clone_at_ref', clone),
        patch.object(code_instruct, 'sample_seed', return_value=Seed('Bio/example.py', 1, 2, 'fixture')),
        patch.object(collector, '_llm_synthesize', return_value=candidate),
        patch.object(code_instruct, 'has_benchmark_overlap', return_value=False),
        patch.object(code_instruct, 'references_task_module', return_value=True),
        patch.object(code_instruct, 'check_repo_anchoring', return_value=(True, '')),
        patch.object(code_instruct, 'check_symbol_collision', return_value=(True, '')),
        patch.object(code_instruct, 'check_test_strength', return_value=(True, '')),
    ):
        result = collector.run(args.output / 'native-run')
    assert result.candidates == 10 and result.emitted == 0
    assert len(collector.records) == 10
    assert result.skip_reasons == {'validation_deferred': 10}
    assert not list((args.output / 'native-run').rglob('task.toml'))
    save_record(args.output / 'checks.json', {'stage': 'offline_collector_contract',
        'collected_fixture_candidates': 10, 'exported_tasks': 0, 'model_calls': 0,
        'validation_executed': False, 'note': 'Native author gates were mocked; this tests staging only.'})
    print('Author-only boundary verified: ten fixture records, no exports or validation')


if __name__ == '__main__':
    main()
