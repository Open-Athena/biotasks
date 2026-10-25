"""Resource completion is independent of reward; only handled timeouts qualify."""


def verify_native_resource_record(agent, metadata, result):
    if metadata["state"] != "completed" or metadata["command_returncode"] != 0:
        raise ValueError("A handled, completed native process is required")
    if metadata["trial_dispatched"] is not True:
        raise ValueError("A completed original trial dispatch is required")
    command = metadata["command"]
    positions = [i for i, value in enumerate(command) if value == "--max-retries"]
    if len(positions) != 1 or command[positions[0] + 1 : positions[0] + 2] != ["0"]:
        raise ValueError("Native retries must be explicitly disabled")
    exception = metadata["exception_type"]
    observed = result.get("exception_info")
    if exception is None:
        if observed is not None:
            raise ValueError("The original result contradicts exception-free metadata")
        return None
    if agent != "terminus-2" or exception != "AgentTimeoutError":
        raise ValueError("Only an ordinary solver deadline can extend this profile")
    if metadata["agent_timeout_sec"] != 600:
        raise ValueError("The solver must retain the approved 600-second limit")
    if not isinstance(observed, dict) or observed.get("exception_type") != exception:
        raise ValueError("The original result must verify the recorded timeout")
    return exception
