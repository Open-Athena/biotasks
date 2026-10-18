"""Small transport fixtures; no repository code, Docker or model execution."""
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

from prepare_biopython_marin_transport import normalization_program


def main():
    content = b'Example public license text\n'
    expected = hashlib.sha256(content).hexdigest()
    with TemporaryDirectory(prefix='biotasks21-license-transport-') as temp:
        root = Path(temp)
        target = root / 'LICENSE.rst'
        target.write_bytes(content)
        target.chmod(0o644)
        link = root / 'LICENSE'
        link.symlink_to('LICENSE.rst')
        run = subprocess.run([sys.executable, '-c', normalization_program(root, expected)], capture_output=True, check=True)
        first = json.loads(run.stdout)
        assert first['before'] == 'symlink:LICENSE.rst' and first['after'] == 'ordinary_file'
        assert link.read_bytes() == target.read_bytes() == content and not link.is_symlink()
        assert link.stat().st_mode & 0o777 == target.stat().st_mode & 0o777 == 0o644
        run = subprocess.run([sys.executable, '-c', normalization_program(root, expected)], capture_output=True, check=True)
        assert json.loads(run.stdout)['before'] == 'ordinary_file'
        link.unlink()
        link.symlink_to('../unrelated-license')
        run = subprocess.run([sys.executable, '-c', normalization_program(root, expected)], capture_output=True)
        assert run.returncode != 0 and link.is_symlink() and os.readlink(link) == '../unrelated-license'
        link.unlink()
        link.symlink_to('LICENSE.rst')
        run = subprocess.run([sys.executable, '-c', normalization_program(root, '0' * 64)], capture_output=True)
        assert run.returncode != 0 and link.is_symlink() and target.read_bytes() == content
    print('Known-link materialization preserves bytes/mode, is idempotent, and rejects unexpected target/hash; repository/model/service calls=0.')


if __name__ == '__main__':
    main()
