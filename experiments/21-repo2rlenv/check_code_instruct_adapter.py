"""Offline contract checks for package mapping and bounded native iteration."""

import argparse
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from code_instruct_adapter import adapted_code_instruct, code_instruct
from repo2rlenv.execution.lifecycle import save_record
from repo2rlenv.spec.options import CodeInstructOptions


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    original_run = code_instruct.CodeInstructPipeline.run
    original_detector = code_instruct.detect_repo_package
    counts = {'seeds': 0, 'author_attempts': 0, 'cleanup': 0}

    def clone(url, ref, token, destination, depth):
        (destination / 'Bio').mkdir(parents=True)
        (destination / 'Bio/__init__.py').write_text('')

    def sample(*args, **kwargs):
        counts['seeds'] += 1
        return SimpleNamespace(relative_path='Bio/example.py', start_line=1, end_line=40)

    def author(self, seed, *, pkg_name):
        assert pkg_name == 'Bio'
        counts['author_attempts'] += 1
        return None

    def cleanup():
        counts['cleanup'] += 1

    recipe = code_instruct.CodeInstructPipeline(
        SimpleNamespace(llm=object(), auth=None, repo=SimpleNamespace(
            access='public', owner_name=('biopython', 'biopython'), url='unused', ref='unused')),
        CodeInstructOptions(limit=3, seed=24),
        SimpleNamespace(image_tag='unused'),
    )
    with adapted_code_instruct(args.output):
        with tempfile.TemporaryDirectory() as tmp:
            try:
                code_instruct.detect_repo_package(Path(tmp), 'biopython')
            except ValueError:
                pass
            else:
                raise AssertionError('Missing package must fail closed')
            (Path(tmp) / 'skbio').mkdir()
            (Path(tmp) / 'skbio/__init__.py').write_text('')
            assert code_instruct.detect_repo_package(Path(tmp), 'scikit-bio') == 'skbio'
        with (
            patch.object(code_instruct, 'resolve_repo_token', return_value=None),
            patch.object(code_instruct, '_shallow_clone_at_ref', clone),
            patch.object(code_instruct, 'sample_seed', sample),
            patch.object(code_instruct.CodeInstructPipeline, '_llm_synthesize', author),
            patch.object(code_instruct.CodeInstructPipeline, '_start_sandbox', return_value=SimpleNamespace(cleanup=cleanup)),
        ):
            result = recipe.run(args.output / 'tasks')
    assert counts == {'seeds': 10, 'author_attempts': 30, 'cleanup': 1}, counts
    assert result.candidates == 10 and result.emitted == 0
    assert code_instruct.CodeInstructPipeline.run is original_run
    assert code_instruct.detect_repo_package is original_detector
    save_record(args.output / 'checks.json', {
        'stage': 'offline_adapter_contract_checks', 'counts': counts,
        'model_calls': 0, 'remote_workers': 0,
        'missing_package_rejected': True, 'native_bindings_restored': True,
        'limitation': 'Mocked author and sandbox; no generation or grading result.',
    })
    print(counts)


if __name__ == '__main__':
    main()
