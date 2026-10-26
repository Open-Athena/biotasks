"""A filtered owner query or an empty cleanup list cannot replace exact IDs."""

import pytest
from verify_snapshot_cleanup import verify_claim_ids_absent


class DaytonaNotFoundError(Exception):
    pass


class Provider:
    def __init__(self, present=None, error=None):
        self.present, self.error, self.seen = present, error, []

    def get(self, identity, **kwargs):
        self.seen.append(identity)
        if self.error:
            raise self.error
        if identity == self.present:
            return object()
        raise DaytonaNotFoundError


def claims():
    return [{"id": str(n), "state": "created"} for n in range(4)]


def test_every_claim_is_queried_without_consulting_cleanup_list_contents():
    provider = Provider()
    verify_claim_ids_absent(provider, claims())
    assert provider.seen == ["0", "1", "2", "3"]


def test_an_original_claim_remaining_blocks_cleanup():
    with pytest.raises(RuntimeError, match="claimed sandbox remains"):
        verify_claim_ids_absent(Provider(present="3"), claims())


def test_an_access_failure_is_not_absence():
    with pytest.raises(PermissionError):
        verify_claim_ids_absent(Provider(error=PermissionError()), claims())


def test_duplicate_claims_cannot_hide_an_unchecked_resource():
    with pytest.raises(AssertionError):
        verify_claim_ids_absent(Provider(), [claims()[0], claims()[0]])
