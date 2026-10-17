"""Verify capture limits with tiny fixtures, including fail-closed preservation."""
import json
import sys
import tempfile
from pathlib import Path
from capture_author_process import capture

with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp)
    for limit in (0, -1, 2*1024**3+1):
        target = root/str(limit)
        try:
            capture([sys.executable, '-c', 'raise AssertionError("must not execute")'],
                    source=target/'source', output=target/'output', timeout=1, maximum_bytes=limit)
        except ValueError:
            assert not target.exists()
        else:
            raise AssertionError('Invalid allowance accepted')
    source = root/'source'
    source.mkdir()
    (source/'fixture').write_bytes(b'12345678')
    for name, limit, succeeds in [('exact',8,True), ('small',7,False), ('remote_cap',2*1024**3,True)]:
        output = root/name
        try:
            result = capture([sys.executable,'-c','pass'],source=source,output=output,timeout=2,maximum_bytes=limit)
        except ValueError:
            assert not succeeds
        else:
            assert succeeds and result==0
        status=json.loads((output/'author-process-status.json').read_text())
        assert status['maximum_evidence_bytes']==limit
        assert status['evidence_preserved']==succeeds
print(json.dumps({'stage':'capture_allowance_regression','invalid_limits_rejected_before_execution':3,'fixture_cases':3,'passed':True,'model_calls':0,'remote_workers':0}))
