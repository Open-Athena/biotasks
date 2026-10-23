"""Verified retention is distinct from permission to publish original evidence."""

PUBLIC_BUCKET = 'open-athena/biotasks'
PRIVATE_BUCKET = 'open-athena/biotasks-restricted'


def route(review):
    visibility = review.get('archive_visibility', 'public')
    if visibility == 'private':
        assert review['public_eligible'] is False
        assert review.get('private_archive_eligible') is True
        assert review.get('archive_bucket') == PRIVATE_BUCKET
        return PRIVATE_BUCKET, visibility
    assert visibility == 'public' and review['public_eligible'] is True
    assert review.get('archive_bucket', PUBLIC_BUCKET) == PUBLIC_BUCKET
    return PUBLIC_BUCKET, visibility


def verified_receipt(receipt, manifest):
    bucket = receipt.get('bucket', PUBLIC_BUCKET)
    visibility = receipt.get('visibility', 'public')
    if manifest.get('archive_bucket', PUBLIC_BUCKET) != bucket:
        return False
    if manifest.get('archive_visibility', 'public') != visibility:
        return False
    if bucket == PUBLIC_BUCKET and visibility == 'public':
        if manifest.get('archive_kind') == 'curated_public_with_local_originals':
            return bool(receipt.get('anonymous_download_verified') is True
                and receipt.get('archive_kind') == manifest['archive_kind']
                and receipt.get('curated_public_bytes_verified') is True
                and receipt.get('full_original_phase_uploaded') is False
                and receipt.get('local_originals_verified') is True
                and receipt.get('local_originals_receipt_sha256') == manifest.get('local_originals_receipt_sha256')
                and receipt.get('local_original_manifest_sha256') == manifest.get('local_original_manifest_sha256')
                and receipt.get('original_phase_sha256') == manifest.get('original_phase_sha256')
                and all(manifest.get(k) for k in ['local_originals_receipt_sha256',
                    'local_original_manifest_sha256', 'original_phase_sha256']))
        return receipt.get('anonymous_download_verified') is True
    return bool(bucket == PRIVATE_BUCKET and visibility == 'private'
        and receipt.get('anonymous_download_verified') is False
        and receipt.get('authenticated_download_verified') is True
        and receipt.get('bucket_private_verified') is True
        and receipt.get('anonymous_access_denied') is True
        and receipt.get('anonymous_http_status') in [401, 403, 404])
