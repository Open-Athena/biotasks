"""Keep successful primary exports distinct from recovered timeout snapshots."""


def check_bootstrap_role(status, *, primary):
    if primary:
        assert status["completed"] is True and status.get("error_type") is None
    else:
        assert status["completed"] is False and status["error_type"] == "TimeoutExpired"


def check_primary_terminal(observations, *, claim_sha256):
    terminal = max(observations, key=lambda row: row["observed_at"])
    assert terminal["terminal"] is True and terminal["state"] == "SUCCEEDED"
    assert terminal["claim_sha256"] == claim_sha256
