"""Retired combined preparation/execution entry point.

The former runner generated dependencies and staging with a text-only worker.
Its recorded implementation remains available at commit 2e1fb637ed0a8dad48e4e8ef9017e49e765d9575.
The replacement execution stage needs tool-enabled setup and is not integrated.
Preparation-only runs use run_preparation.py.
"""

EXECUTION_PENDING = (
    "The combined reference runner is retired. Tool-enabled dependency and input "
    "setup is not integrated yet; use preparation-only runs for inspection."
)


async def run(config, *, seed, root, deadline, endpoint, credential):
    raise NotImplementedError(EXECUTION_PENDING)


if __name__ == "__main__":
    raise SystemExit(EXECUTION_PENDING)
