"""Synthetic child-process checks; no repository, model or provider execution."""
import json
import sys
import tarfile
import tempfile
from pathlib import Path

from capture_author_process import capture


def main():
    records = []
    with tempfile.TemporaryDirectory() as tmp:
        for case, ending, expected in [('success', '', 0), ('failure', 'raise SystemExit(7)', 7),
                                        ('timeout', 'import time; time.sleep(10)', 124)]:
            root = Path(tmp) / case
            source, output = root / 'author', root / 'capture'
            command = [sys.executable, '-c',
                       'from pathlib import Path; import sys; '
                       'p=Path(sys.argv[1]); p.mkdir(parents=True); '
                       '(p/"partial.txt").write_text("preserved"); '
                       'print("child stdout",flush=True); '
                       'print("child stderr",file=sys.stderr,flush=True); ' + ending,
                       str(source)]
            code = capture(command, source=source, output=output, timeout=0.5)
            assert code == expected
            status = json.loads((output / 'author-process-status.json').read_text())
            assert status['evidence_preserved']
            assert (output / 'author.stdout').read_text() == 'child stdout\n'
            assert (output / 'author.stderr').read_text() == 'child stderr\n'
            with tarfile.open(output / 'author-evidence.tar.gz') as archive:
                assert archive.extractfile('author-output/partial.txt').read() == b'preserved'
            try:
                capture(command, source=source, output=output, timeout=0.5)
            except FileExistsError:
                pass
            else:
                raise AssertionError('Existing attempt was overwritten')
            records.append({'case': case, 'exit_code': code, 'state': status['state'],
                            'partial_evidence_verified': True, 'overwrite_rejected': True})
    dest = Path(__file__).parent / 'evidence/code-instruct-capture-diagnosis/capture-check.json'
    dest.write_text(json.dumps({'stage': 'synthetic_capture_check', 'records': records,
                               'model_calls': 0, 'remote_allocations': 0}, indent=2) + '\n')
    print(json.dumps(records))


if __name__ == '__main__':
    main()
