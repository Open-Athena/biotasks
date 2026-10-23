"""Adversarial publication/retention boundaries; no network, native test or model calls."""

from copy import deepcopy

from curated_matchms import allow_member
from retention import verified_receipt


def main():
    assert allow_member('outputs/matchms__matchms/matchms__matchms-194/tests/f2p.json')
    assert allow_member('jobs/fresh/matchms__matchms-194-oracle/trial/verifier/reward-details.json')
    for path in ['native-observations/batch-0000/exec-0001-pr-110.json.gz',
            'native-observations/batch-0000/validation-001-pr-110.json.gz',
            'native-observations/batch-0000/events.jsonl',
            'outputs/matchms__matchms/matchms__matchms-194/tests/test.sh',
            'outputs/matchms__matchms/matchms__matchms-194/solution/patch.diff',
            'jobs/fresh/matchms__matchms-194-oracle/trial/verifier/test_output.log',
            'outputs/other/fixture/verifier.py', 'native-observations/fake/billing.json']:
        assert allow_member(path) is None, path
    for path in ['../reward.txt', '/absolute/reward.txt']:
        try:
            allow_member(path)
        except AssertionError:
            pass
        else:
            raise AssertionError('Unsafe member path accepted')
    kind = 'curated_public_with_local_originals'
    manifest = {'archive_kind': kind, 'archive_bucket': 'open-athena/biotasks', 'archive_visibility': 'public',
        'local_originals_receipt_sha256': 'local-receipt', 'local_original_manifest_sha256': 'private-manifest',
        'original_phase_sha256': 'original-phase'}
    receipt = {'bucket': 'open-athena/biotasks', 'visibility': 'public', 'archive_kind': kind,
        'anonymous_download_verified': True, 'curated_public_bytes_verified': True,
        'full_original_phase_uploaded': False, 'local_originals_verified': True,
        **{k: manifest[k] for k in ['local_originals_receipt_sha256', 'local_original_manifest_sha256', 'original_phase_sha256']}}
    assert verified_receipt(receipt, manifest)
    for key in ['local_originals_verified', 'curated_public_bytes_verified', 'anonymous_download_verified']:
        broken = deepcopy(receipt); broken[key] = False
        assert not verified_receipt(broken, manifest)
    for key in ['local_originals_receipt_sha256', 'local_original_manifest_sha256', 'original_phase_sha256']:
        broken = deepcopy(receipt); broken[key] = 'other'
        assert not verified_receipt(broken, manifest)
    assert not verified_receipt({**receipt, 'full_original_phase_uploaded': True}, manifest)
    assert not verified_receipt({'anonymous_download_verified': True}, manifest)
    assert verified_receipt({'anonymous_download_verified': True}, {})
    print('Split retention boundaries pass: raw commands/patches/logs rejected, unsafe paths rejected, curated bytes cannot masquerade as originals, local hash/receipt binding mandatory; legacy public contract unchanged.')


if __name__ == '__main__':
    main()
