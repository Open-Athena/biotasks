"""Check public archive admission rejects unsafe paths, links, binaries and secrets."""
import io
import json
from pathlib import Path
import tarfile

from preserve_macs_evidence import inspect_archive


def archive(name, data=b'public fixture\n', symlink=False):
    out = io.BytesIO()
    with tarfile.open(fileobj=out, mode='w:gz') as tar:
        member = tarfile.TarInfo(name)
        member.size = len(data)
        if symlink:
            member.type = tarfile.SYMTYPE
            member.linkname = '/etc/passwd'
            member.size = 0
        tar.addfile(member, io.BytesIO(data) if not symlink else None)
    return out.getvalue()


def main():
    assert inspect_archive(archive('ok.txt'), 'tar.gz')[0]['bytes'] == 15
    rows = []
    for name, data in [('parent_path', archive('../bad.txt')),
                       ('absolute_path', archive('/bad.txt')),
                       ('symlink', archive('link', symlink=True)),
                       ('binary', archive('binary.dat', b'\xff\xfe')),
                       ('credential', archive('secret.txt', b'ghp_' + b'0' * 30))]:
        try:
            inspect_archive(data, 'tar.gz')
        except (AssertionError, UnicodeDecodeError):
            rows.append({'case': name, 'rejected': True})
        else:
            raise AssertionError(name + ' was accepted')
    result = {'synthetic_only': True, 'safe_text_accepted': True, 'rejection_checks': rows, 'remote_calls': 0}
    (Path(__file__).parent / 'archive-scan-checks.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
