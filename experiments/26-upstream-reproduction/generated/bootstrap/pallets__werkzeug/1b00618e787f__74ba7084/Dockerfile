# Auto-generated from r2e-bootstrap agent transcript.
# Build from the cloned repo root: `docker build -t my-image .`
FROM python:3.12-slim
WORKDIR /workspace
COPY . /workspace

RUN ls /workspace && cat /workspace/pyproject.toml 2>/dev/null || cat /workspace/setup.py 2>/dev/null || cat /workspace/setup.cfg 2>/dev/null | head -50
RUN cd /workspace && pip install -e ".[tests]" -q && pip install pytest pytest-timeout -q && python -m pytest --collect-only -q 2>&1 | tail -20
RUN cd /workspace && pip install cffi cryptography ephemeral-port-reserve pytest pytest-timeout watchdog -q && python -m pytest --collect-only -q 2>&1 | tail -20
