"""Keep explicit fallback recovery within its original campaign namespace."""

import re


def campaign_prefix(number, explicit=None):
    if type(number) is not int or not 196 <= number <= 999:
        raise ValueError("Expected a supported original campaign number")
    if explicit is None:
        if number > 205:
            raise ValueError("Later campaign recovery requires its explicit original prefix")
        return f"s3://marin-us-east-02a/marin/evals/biotasks19/20261026-panel101/biotasks19-autonomous-panel-{number:03}/"
    pattern = rf"s3://marin-us-east-02a/marin/evals/biotasks19/[0-9]{{8}}-panel[0-9]{{3}}/biotasks19-autonomous-panel-{number:03}/"
    if not isinstance(explicit, str) or not re.fullmatch(pattern, explicit):
        raise ValueError("Recovery prefix must identify this exact original campaign")
    return explicit
