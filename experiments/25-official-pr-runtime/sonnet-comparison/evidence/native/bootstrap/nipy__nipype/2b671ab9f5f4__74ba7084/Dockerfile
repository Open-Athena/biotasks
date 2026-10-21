# Auto-generated from r2e-bootstrap agent transcript.
# Build from the cloned repo root: `docker build -t my-image .`
FROM python:3.12-slim
WORKDIR /workspace
COPY . /workspace

RUN ls /workspace && cat /workspace/pyproject.toml 2>/dev/null || cat /workspace/setup.py 2>/dev/null | head -50
RUN cd /workspace && HATCH_VCS_PRETEND_VERSION=0.0.0 pip install -e ".[tests]" -q 2>&1 | tail -20
RUN cd /workspace && HATCH_VCS_PRETEND_VERSION=0.0.0 pip install -e ".[tests]" 2>&1 | grep -E "(error|Error|Successfully|already)" | head -20
RUN cd /workspace && pip install hatch-vcs hatchling -q && HATCH_VCS_PRETEND_VERSION=0.0.0 pip install -e ".[tests]" -q 2>&1 | tail -20
RUN cd /workspace && SETUPTOOLS_SCM_PRETEND_VERSION=0.0.0 pip install -e ".[tests]" -q 2>&1 | tail -20
RUN cd /workspace && python -m pytest --collect-only -q 2>&1 | tail -30
