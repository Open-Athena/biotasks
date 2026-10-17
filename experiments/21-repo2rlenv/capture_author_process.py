"""Capture an author child and partial evidence in supported attempt storage."""
import hashlib
import json
import os
import signal
import subprocess
import time
from pathlib import Path

from preserve_author_output import preserve


def capture(command, *, source, output, timeout, env=None):
    source, output = Path(source), Path(output)
    output.mkdir(parents=True, exist_ok=True)
    status_path = output / 'author-process-status.json'
    if status_path.exists():
        raise FileExistsError(status_path)
    status = {'stage': 'author_process', 'state': 'started', 'timeout_seconds': timeout}
    status_path.write_text(json.dumps(status, indent=2) + '\n')
    started = time.monotonic()
    child = None
    code = 1
    try:
        with (output / 'author.stdout').open('xb') as stdout, (output / 'author.stderr').open('xb') as stderr:
            child = subprocess.Popen(command, env=env, stdout=stdout, stderr=stderr,
                                     start_new_session=True)
            try:
                code = child.wait(timeout=timeout)
                status['state'] = 'completed' if code == 0 else 'failed'
            except subprocess.TimeoutExpired:
                status['state'] = 'timed_out'
                code = 124
            finally:
                # Only the process group created by this call is owned here.
                try:
                    os.killpg(child.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                child.wait()
        return code
    except Exception as exc:
        status.update(state='launcher_failed', error_type=type(exc).__name__)
        raise
    finally:
        status.update(exit_code=code, elapsed_seconds=round(time.monotonic() - started, 3))
        try:
            if source.is_dir() and any(p.is_file() for p in source.rglob('*')):
                receipt_path = output / 'author-evidence-receipt.json'
                if receipt_path.exists():
                    receipt = json.loads(receipt_path.read_text())
                    h = hashlib.sha256()
                    with (output / 'author-evidence.tar.gz').open('rb') as stream:
                        for block in iter(lambda: stream.read(65536), b''):
                            h.update(block)
                    assert h.hexdigest() == receipt['sha256']
                else:
                    receipt = preserve(source, output)
                status.update(evidence_preserved=True, evidence_sha256=receipt['sha256'])
            else:
                status['evidence_preserved'] = False
        except Exception as exc:
            status.update(evidence_preserved=False, preservation_error=type(exc).__name__)
            raise
        finally:
            status_path.write_text(json.dumps(status, indent=2) + '\n')
