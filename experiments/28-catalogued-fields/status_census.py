"""Count retained statuses with the exact pinned upstream parser; never assign reward."""

import argparse
from collections import Counter
import hashlib
import importlib.util
import json
from pathlib import Path
import shlex

ROOT = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--results', type=Path, required=True)
    args = parser.parse_args()
    source = ROOT / 'preflight/upstream_verifier.py'
    expected = json.loads((ROOT / 'preflight/upstream-verifier-source.json').read_text())['sha256']
    assert hashlib.sha256(source.read_bytes()).hexdigest() == expected
    spec = importlib.util.spec_from_file_location('original_upstream_verifier', source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    expanded = args.results / 'expanded'
    rows = []
    for path in sorted((expanded / 'jobs/fresh').glob('*/*/result.json')):
        result = json.loads(path.read_text())
        task = path.parent.parent.name.rsplit('-', 1)[0]
        task_root = next((expanded / 'outputs').glob('*/' + task))
        verifier = task_root / 'tests/verifier.py'
        assert hashlib.sha256(verifier.read_bytes()).hexdigest() == expected
        script = (task_root / 'tests/test.sh').read_text()
        command_line = next(line for line in script.splitlines() if line.startswith('python3 "$SCRIPT_DIR/verifier.py"'))
        tokens = shlex.split(command_line)
        runner = module._detect_runner(tokens[tokens.index('--test-cmds') + 1])
        log = path.parent / 'verifier/test_output.log'
        assert not log.exists() or log.stat().st_size <= 16 * 1024**2
        statuses = module.parse_logs(runner, log.read_text(errors='replace')) if log.exists() else {}
        details_path = path.parent / 'verifier/reward-details.json'
        details = json.loads(details_path.read_text()) if details_path.exists() else {}
        rows.append({'trial': str(path.relative_to(expanded)), 'runner': runner,
            'retained_status_counts': dict(Counter(statuses.values())), 'retained_tests_parsed': len(statuses),
            'complete_trial': bool(result.get('finished_at') and not result.get('exception_info')),
            'exception': (result.get('exception_info') or {}).get('exception_type'),
            'matches_graded_test_count': len(statuses) == details['tests_parsed'] if 'tests_parsed' in details else None,
            'retained_census_is_partial': not bool(result.get('finished_at') and not result.get('exception_info'))})
    output = {'method': 'Exact unmodified pinned standalone verifier parse_logs; status census only, no regrading or test execution.',
              'source_sha256': expected, 'trials': rows}
    (args.results / 'retained-status-census.json').write_text(json.dumps(output, indent=2) + '\n')
    print(json.dumps(output, indent=2))


if __name__ == '__main__':
    main()
