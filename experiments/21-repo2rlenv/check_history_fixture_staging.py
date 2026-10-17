"""Compare native test-root staging on recovered source; no repository execution."""
import argparse
import hashlib
import inspect
import json
import tempfile
from pathlib import Path

from repo2rlenv.pipelines.recipes.history.test_suite import stage_tests
from repo2rlenv.spec.recipe_options import R2EGymOptions


def run(head, output):
    root = Path(__file__).parent
    original = json.loads((root / 'r2e-gym-skbio-profile.json').read_text())
    adapted = json.loads((root / 'r2e-gym-skbio-fixtures-profile.json').read_text())
    before = R2EGymOptions.model_validate(original['options'])
    after = R2EGymOptions.model_validate(adapted['options'])
    a, b = before.model_dump(), after.model_dump()
    assert {key for key in a if a[key] != b[key]} == {'test_paths'}
    data_root = 'skbio/stats/composition/tests/data'
    assert after.test_paths == [*before.test_paths, data_root]
    selected = before.test_paths
    expected = {str(p.relative_to(head)): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in (head / data_root).rglob('*') if p.is_file()}
    assert expected and data_root + '/atlas_feature_table.csv' in expected
    with tempfile.TemporaryDirectory() as tmp:
        old, new = Path(tmp) / 'original', Path(tmp) / 'adapted'
        old.mkdir(); new.mkdir()
        old_tests = stage_tests(head, old, selected, before.test_paths)
        new_tests = stage_tests(head, new, selected, after.test_paths)
        assert old_tests == new_tests
        for path, digest in expected.items():
            assert not (old / 'r2e_tests' / path).exists()
            assert hashlib.sha256((new / 'r2e_tests' / path).read_bytes()).hexdigest() == digest
        for path in selected:
            assert (old / 'r2e_tests' / path).read_bytes() == (new / 'r2e_tests' / path).read_bytes()
    report = {'stage': 'native_staging_comparison_only',
              'source_revision': original['repo']['ref'],
              'source_sha256': hashlib.sha256(Path(inspect.getfile(stage_tests)).read_bytes()).hexdigest(),
              'changed_option': 'test_paths adds existing fixture directory',
              'test_selection_unchanged': True, 'test_bytes_unchanged': True,
              'fixture_files': expected, 'restored_fixture_count': len(expected),
              'runtime_test_execution': False, 'model_calls': 0, 'remote_allocations': 0,
              'remaining': 'Separate adapted remote old/new contrast, authoring, export and acceptance.'}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--head', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    run(args.head, args.output)
