"""Exercise complete, missing and inconsistent evidence without services."""
import hashlib
import io
import json
import tarfile
import tempfile
from pathlib import Path

from contrast_summary import summarize


def pack(root, data):
    archive = root / 'native-evidence.tar.gz'
    with tarfile.open(archive, 'w:gz') as handle:
        raw = json.dumps(data).encode()
        member = tarfile.TarInfo('native/generation/generation.json')
        member.size = len(raw)
        handle.addfile(member, io.BytesIO(raw))
    return archive


def main():
    with tempfile.TemporaryDirectory(prefix='biotasks21-summary-') as tmp:
        root = Path(tmp)
        (root / 'workers').mkdir()
        (root / 'workers/one.json').write_text(json.dumps({'worker_id': 'owned', 'state': 'terminated', 'spec': {'api_key_env': 'NOT_A_VALUE'}, 'private_unrelated_field': 'not-exported'}))
        missing = summarize(root, root / 'small.json')
        assert not missing['generation_available'] and missing['workers'] == [{'worker_id': 'owned', 'state': 'terminated'}]
        original = {'attempted': 2, 'candidates': [{'id': 'one', 'entity': 'f', 'source_file': 'module.py'}], 'rejected': [{'id': 'two'}]}
        archive = pack(root, original)
        good = summarize(root, root / 'small.json')
        assert good['attempted'] == 2 and good['execution_passed'] == 1 and good['rejected'] == 1
        assert good['native_archive_sha256'] == hashlib.sha256(archive.read_bytes()).hexdigest()
        pack(root, {**original, 'attempted': 3})
        try:
            summarize(root, root / 'small.json')
        except ValueError:
            pass
        else:
            raise AssertionError('Inconsistent historical counts accepted')
    print('Contrast summary controls passed: partial evidence, cleanup-field whitelist, original hash, counts and inconsistency rejection.')


if __name__ == '__main__':
    main()
