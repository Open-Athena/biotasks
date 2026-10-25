"""Narrow official configuration surface, shared by planning and worker guards."""

DISCOVERY_KEYS = {"limit", "since", "until"}
OPTIONAL_KEYS = {"require_new_test_funcs"}


def accepts(options):
    return (
        isinstance(options, dict)
        and DISCOVERY_KEYS <= set(options) <= DISCOVERY_KEYS | OPTIONAL_KEYS
        and (
            "require_new_test_funcs" not in options
            or type(options["require_new_test_funcs"]) is bool
        )
    )


def matches(options, snapshot):
    if not accepts(options) or not isinstance(snapshot, dict):
        return False
    optional = "require_new_test_funcs"
    if (optional in options) != (optional in snapshot):
        return False
    if optional in options and (
        type(snapshot[optional]) is not bool or options[optional] is not snapshot[optional]
    ):
        return False
    return all(key in snapshot and options[key] == snapshot[key] for key in DISCOVERY_KEYS)
