# Auto-generated from r2e-bootstrap agent transcript.
# Build from the cloned repo root: `docker build -t my-image .`
FROM python:3.12-slim
WORKDIR /workspace
COPY . /workspace

RUN ls /workspace && head -60 /workspace/pyproject.toml 2>/dev/null; head -40 /workspace/setup.py 2>/dev/null; ls /workspace/requirements*.txt 2>/dev/null
RUN sed -n 60,120p /workspace/pyproject.toml; ls /workspace/*requirements* 2>/dev/null; cat /workspace/requirements.txt 2>/dev/null | headThought: Check the rest of pyproject for test extras.
RUN HATCH_VCS_PRETEND_VERSION=0.0.0 pip install -e .[tests] 2>&1 | tail -5Observation: \
    exit=0 \
    Successfully installed ... (many packages)
RUN HATCH_VCS_PRETEND_VERSION=0.0.0 pip install -e '.[tests]' > /tmp/pip.log 2>&1; echo EXIT=$?; tail -n 3 /tmp/pip.log
RUN grep -i -m5 -E 'error|failed' /tmp/pip.log | head -20
RUN HATCH_VCS_PRETEND_VERSION=0.0.0 SETUPTOOLS_SCM_PRETEND_VERSION=0.0.0 pip install -e '.[tests]' > /tmp/pip.log 2>&1; echo EXIT=$?; tail -n 3 /tmp/pip.log
RUN cd /workspace && python -m pytest --collect-only -q > /tmp/collect.log 2>&1; echo EXIT=$?; tail -n 15 /tmp/collect.log
