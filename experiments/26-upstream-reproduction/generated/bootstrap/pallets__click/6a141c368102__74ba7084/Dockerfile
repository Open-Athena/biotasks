# Auto-generated from r2e-bootstrap agent transcript.
# Build from the cloned repo root: `docker build -t my-image .`
FROM python:3.12-slim
WORKDIR /workspace
COPY . /workspace

RUN ls /workspace && cat /workspace/pyproject.toml 2>/dev/null || cat /workspace/setup.py 2>/dev/null || cat /workspace/setup.cfg 2>/dev/null
RUN cd /workspace && pip install -e ".[tests]" 2>&1 | tail -20 || pip install -e . && pip install pytest 2>&1 | tail -10
RUN cd /workspace && python -m pytest --collect-only -q 2>&1 | tail -20
RUN pip install "pytest<9" 2>&1 | tail -10
RUN cd /workspace && python -m pytest --collect-only -q 2>&1 | tail -10
