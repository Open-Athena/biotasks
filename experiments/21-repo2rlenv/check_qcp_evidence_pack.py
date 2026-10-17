"""Check reconstructability, retained reports/modes, and changed-asset rejection."""
import hashlib
import json
import tarfile
import tempfile
from pathlib import Path
from pack_qcp_evidence import pack

with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp) / 'native'
    bundles = root / 'independent/bundles'
    assets = {'environment/source/example.py': b'original\n', 'tests/test.sh': b'check\n'}
    cases = [{'case': name} for name in ['baseline', 'reference']]
    for case in cases:
        task = bundles / case['case']
        for rel, data in assets.items():
            p = task / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(data)
        solution = task / 'solution/solve.sh'
        solution.parent.mkdir()
        solution.write_text('#!/bin/sh\ntrue\n')
        solution.chmod(0o755)
    manifest = {'cases': cases, 'source_bundle_hash': 'sha256:fixture',
                'unchanged_assets': {k: hashlib.sha256(v).hexdigest() for k,v in assets.items()}}
    (bundles / 'manifest.json').write_text(json.dumps(manifest))
    report = root / 'independent/jobs/reference/result.json'
    report.parent.mkdir(parents=True)
    report.write_text('{"reward":1}\n')
    target = Path(tmp) / 'evidence.tar.gz'
    receipt = pack(root, target)
    assert receipt['omitted_duplicate_files'] == 4
    with tarfile.open(target) as archive:
        names = archive.getnames()
        assert 'native/independent/jobs/reference/result.json' in names
        assert 'native/independent/bundles/manifest.json' in names
        assert not any('/environment/' in n or '/tests/' in n for n in names)
        for case in cases:
            member = archive.getmember('native/independent/bundles/' + case['case'] + '/solution/solve.sh')
            assert member.mode == 0o755
            assert archive.extractfile(member).read() == b'#!/bin/sh\ntrue\n'
    (bundles / 'reference/tests/test.sh').write_text('changed')
    try:
        pack(root, Path(tmp) / 'invalid.tar.gz')
    except ValueError:
        pass
    else:
        raise AssertionError('Changed assets silently omitted')
    assert not (Path(tmp) / 'invalid.tar.gz').exists()
print('PASS: reports, solution modes, exact duplicate omission, changed-asset rejection')
