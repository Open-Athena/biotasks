"""Run the generation adapter in the configured SDK interpreter, ABI isolated."""

import json
import subprocess
from pathlib import Path

from biotasks.validation import bridge
from biotasks.validation.files import MAX_ARCHIVE, require


def call(backend, request, log):
    package = Path(bridge.__file__).resolve().parents[1]
    script = Path(__file__).with_name("generation_client.py")
    launcher = """import runpy, sys, types
package = types.ModuleType('biotasks')
package.__path__ = [sys.argv[1]]
sys.modules['biotasks'] = package
from pathlib import Path
sys.path.insert(0, str(Path(sys.argv[2]).parent))
runpy.run_path(sys.argv[2], run_name='__main__')
"""
    result = subprocess.run(
        [backend["python"], "-c", launcher, str(package), str(script)],
        input=json.dumps({**request, "backend": backend}),
        capture_output=True,
        text=True,
        timeout=180,
        check=False,
    )
    require(
        len(result.stdout) + len(result.stderr) <= MAX_ARCHIVE,
        "Generation transport output exceeds bound",
    )
    log.parent.mkdir(parents=True, exist_ok=True)
    log.write_text(result.stdout + "\n" + result.stderr)
    rows = [
        s[len(bridge.MARKER) :] for s in result.stdout.splitlines() if s.startswith(bridge.MARKER)
    ]
    require(
        result.returncode == 0 and len(rows) == 1,
        "Generation transport failed; inspect protected log",
    )
    return json.loads(rows[0])
