"""Exercise the pinned parser dispatcher without building or running repositories."""
import hashlib
import inspect
import json
from pathlib import Path

import repo2rlenv.log_parsers as parsers


def main():
    cases = [
        ('bedtools_shell', ['bash test.sh'], 'cpp', 'intersection: ok\n'),
        ('bedtools_make', ['make test'], 'cpp', 'intersection: ok\n'),
        ('r_testthat', ["Rscript -e 'testthat::test_dir(\"tests/testthat\")'"],
         'r', '[ FAIL 0 | WARN 0 | SKIP 0 | PASS 2 ]\n'),
        ('python_control', ['pytest -v'], 'python', 'tests/test_example.py::test_one PASSED\n'),
    ]
    rows = []
    for name, commands, language, log in cases:
        result = parsers.parse_logs(commands, log, language=language)
        if name == 'python_control':
            assert len(result) == 1
        else:
            assert result == {}
        rows.append({'case': name, 'commands': commands, 'language': language,
                     'synthetic_log': log, 'recognized_runner': parsers._detect_runner(commands),
                     'parsed_test_count': len(result)})
    source = Path(inspect.getfile(parsers))
    record = {
        'stage': 'local_native_parser_dispatch_probe',
        'generator_revision': '27d04ee8203cd5b2f20c3997d13836e5f5b64238',
        'source_path': 'src/repo2rlenv/log_parsers/__init__.py',
        'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
        'fixtures': 'Synthetic runner text, not repository execution logs.',
        'cases': rows, 'repository_builds': 0, 'repository_tests': 0,
        'model_calls': 0,
        'finding': 'Pinned dispatch recognizes neither these shell/make commands with cpp fallback nor Rscript/testthat with r fallback. Both return empty maps before runner-specific parsing. A C++ or R runtime profile requires an explicit parser adaptation; this does not imply repository incompatibility.'}
    dest = Path(__file__).parent / 'evidence/nonpython-parser-coverage'
    dest.mkdir(exist_ok=True)
    (dest / 'result.json').write_text(json.dumps(record, indent=2) + '\n')
    print(json.dumps(record))


if __name__ == '__main__':
    main()
