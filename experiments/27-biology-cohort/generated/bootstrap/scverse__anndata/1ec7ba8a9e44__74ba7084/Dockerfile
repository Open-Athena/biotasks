# Auto-generated from r2e-bootstrap agent transcript.
# Build from the cloned repo root: `docker build -t my-image .`
FROM python:3.12-slim
WORKDIR /workspace
COPY . /workspace

RUN ls /workspace && cat /workspace/pyproject.toml | head -100
RUN cat /workspace/pyproject.toml | tail -100
RUN python --version && cat /workspace/pyproject.toml | grep -A 50 "test-min"
RUN apt-get update -qq && apt-get install -y -qq git build-essential curl ca-certificates software-properties-common 2>/dev/null | tail -5
RUN apt-get install -y python3.13 python3.13-dev python3.13-venv 2>&1 | tail -10
RUN python3.13 --version && python3.13 -m venv /workspace/.venv && /workspace/.venv/bin/pip install --upgrade pip -q
RUN cd /workspace && HATCH_VCS_PRETEND_VERSION=0.0.0 /workspace/.venv/bin/pip install -e ".[dask,lazy]" -q 2>&1 | tail -20
RUN cd /workspace && SETUPTOOLS_SCM_PRETEND_VERSION=0.0.0 /workspace/.venv/bin/pip install -e ".[dask,lazy]" -q 2>&1 | tail -20
RUN cd /workspace && SETUPTOOLS_SCM_PRETEND_VERSION=0.0.0 /workspace/.venv/bin/pip install pytest pytest-xdist pytest-mock pytest-randomly awkward boltons filelock joblib jsonschema matplotlib openpyxl pooch pyarrow scikit-learn fast-array-utils -q 2>&1 | tail -10
RUN cd /workspace && SETUPTOOLS_SCM_PRETEND_VERSION=0.0.0 /workspace/.venv/bin/python -m pytest --collect-only -q 2>&1 | head -50
RUN cd /workspace && /workspace/.venv/bin/python -m pytest --collect-only -q 2>&1 | tail -10
