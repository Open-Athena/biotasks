"""Exact-worker cleanup wrapper around the unchanged ownership helper."""
import json
import os
from pathlib import Path

from common import sha


def main():
    root=Path(__file__).resolve().parent
    manifest=json.loads((root/'cleanup-payload.json').read_text())
    assert os.environ['IRIS_WORKER_ID']==os.environ['BIOTASKS_EXPECTED_WORKER']
    assert os.environ['BIOTASKS_CLEANUP_RUN']==manifest['primary_run_id']
    for name,digest in manifest['sha256'].items():assert sha(root/name)==digest
    try:
        from cleanup_owned import main as cleanup
        cleanup()
    finally:
        for name in ['docker','docker.tgz']:
            (root/name).unlink(missing_ok=True)
    result=json.loads((Path(os.environ['IRIS_OUTPUT_DIR'])/'cleanup-result.json').read_text())
    assert result['run_id']==manifest['primary_run_id'] and result['verified_empty']
    (Path(os.environ['IRIS_OUTPUT_DIR'])/'cleanup-envelope.json').write_text(json.dumps(dict(
        primary_run_id=manifest['primary_run_id'],worker_id=os.environ['IRIS_WORKER_ID'],
        payload_sha256=manifest['sha256'],cleanup_result_sha256=sha(Path(os.environ['IRIS_OUTPUT_DIR'])/'cleanup-result.json'),
        downloaded_tools_removed=True),indent=2)+'\n')


if __name__=='__main__':main()
