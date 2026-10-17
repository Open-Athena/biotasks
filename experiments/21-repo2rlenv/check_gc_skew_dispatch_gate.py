"""Reject altered or unreviewed control inputs before allocating a worker."""
import contextlib
import io
import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch
import run_smith_controls as runner

with tempfile.TemporaryDirectory() as tmp:
    root=Path(tmp);archive=root/'archive';archive.write_bytes(b'fixture')
    config=root/'config.json'
    for record in ({'candidate_id':'unknown'},
                   {'candidate_id':'5a16004c2d7522727d44','archive_sha256':'changed'}):
        config.write_text(json.dumps(record))
        args=['check','--stage','gc-skew-independent','--campaign',str(root/'campaign'),
              '--worker-name','fixture','--source-archive',str(archive),
              '--generation-archive',str(archive),'--config',str(config)]
        with patch.object(sys,'argv',args),patch.object(runner,'provision_worker') as provision,contextlib.redirect_stderr(io.StringIO()):
            try:runner.main()
            except SystemExit as exc:assert exc.code==2
            else:raise AssertionError('Invalid controls accepted')
            provision.assert_not_called()
        assert not (root/'campaign').exists()
print('PASS: unknown task and changed archive reject before campaign creation or remote allocation')
