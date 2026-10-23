"""Prevent private-retention evidence from masquerading as public byte verification."""

from copy import deepcopy
import datetime
import hashlib
import json
from pathlib import Path

from retention import PRIVATE_BUCKET, PUBLIC_BUCKET, route, verified_receipt

ROOT = Path(__file__).resolve().parent


def reject(review):
    try:
        route(review)
    except AssertionError:
        return
    raise AssertionError('Unsafe or ambiguous publication route accepted')


def main():
    assert route({'public_eligible': True}) == (PUBLIC_BUCKET, 'public')
    review = {'public_eligible': False, 'private_archive_eligible': True,
        'archive_visibility': 'private', 'archive_bucket': PRIVATE_BUCKET}
    assert route(review) == (PRIVATE_BUCKET, 'private')
    reject({'public_eligible': False})
    reject({**review, 'public_eligible': True})
    reject({**review, 'archive_bucket': PUBLIC_BUCKET})
    reject({**review, 'private_archive_eligible': False})
    public = {'bucket': PUBLIC_BUCKET, 'anonymous_download_verified': True}
    assert verified_receipt(public, {})
    assert not verified_receipt({**public, 'anonymous_download_verified': False}, {})
    manifest = {'archive_bucket': PRIVATE_BUCKET, 'archive_visibility': 'private'}
    receipt = {'bucket': PRIVATE_BUCKET, 'visibility': 'private',
        'anonymous_download_verified': False, 'authenticated_download_verified': True,
        'bucket_private_verified': True, 'anonymous_access_denied': True, 'anonymous_http_status': 401}
    assert verified_receipt(receipt, manifest)
    for key in ['authenticated_download_verified', 'bucket_private_verified', 'anonymous_access_denied']:
        broken = deepcopy(receipt); broken[key] = False
        assert not verified_receipt(broken, manifest)
    for updates in [{'anonymous_download_verified': True}, {'anonymous_http_status': 500},
        {'anonymous_http_status': 200}, {'bucket': PUBLIC_BUCKET}, {'visibility': 'public'}]:
        assert not verified_receipt({**receipt, **updates}, manifest)
    assert not verified_receipt(receipt, {})
    assert not verified_receipt(public, manifest)
    actual = []
    for path in sorted((ROOT / 'archives').glob('*-receipt.json')):
        slug = path.name.removesuffix('-receipt.json')
        manifest_path = ROOT / 'archives' / (slug + '-manifest.json')
        if not manifest_path.exists():
            continue
        assert verified_receipt(json.loads(path.read_text()), json.loads(manifest_path.read_text()))
        actual.append(slug)
    result = {'checked_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'scope': 'Local receipt/route contract and existing receipt compatibility only; not a live upload or private byte-readback claim.',
        'passed': True, 'existing_archives_compatible': actual,
        'protected_cases': ['public denial', 'mixed-license public route rejected',
            'private route must be explicit', 'wrong bucket/visibility rejected',
            'authenticated readback required', 'private bucket proof required',
            'anonymous denial required', 'HTTP/network failure is not privacy proof',
            'private readback cannot claim anonymous verification'],
        'source_sha256': {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
            for p in [ROOT / 'retention.py', Path(__file__)]}, 'model_native_or_external_calls': 0}
    (ROOT / 'retention-check.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
