"""One explicit native GLM effort shared by all workers and the blind solver."""


def native_effort(config):
    effort = config.get("reasoning_effort", "high")
    if effort not in ("low", "high", "max"):
        raise ValueError("GLM-5.3 native reasoning_effort must be low, high or max")
    return effort
