"""Conservative controller reservations, distinct from provider invoices."""

from decimal import Decimal, InvalidOperation

SANDBOX_STAGES = ("setup", "replay", "construction", "grading", "native")
STAGE_RESERVATION_USD = Decimal("1.00")
MAX_CAMPAIGN_RESERVATION_USD = Decimal("5.00")


def require_full_pipeline_budget(config):
    """Refuse a full launch that cannot reserve every mandatory sandbox stage."""
    try:
        value = Decimal(str(config["daytona_budget_usd"]))
    except (KeyError, InvalidOperation, TypeError, ValueError) as error:
        raise ValueError("An explicit finite campaign reservation is required") from error
    required = len(SANDBOX_STAGES) * STAGE_RESERVATION_USD
    if not value.is_finite() or not required <= value <= MAX_CAMPAIGN_RESERVATION_USD:
        raise ValueError(
            f"Full autonomous execution requires {required} USD in stage reservations "
            f"and permits at most {MAX_CAMPAIGN_RESERVATION_USD} USD; this is not an invoice"
        )
    return value
