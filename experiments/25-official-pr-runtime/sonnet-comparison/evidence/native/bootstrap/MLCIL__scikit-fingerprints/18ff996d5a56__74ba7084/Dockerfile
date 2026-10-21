# Auto-generated from r2e-bootstrap agent transcript.
# Build from the cloned repo root: `docker build -t my-image .`
FROM python:3.12-slim
WORKDIR /workspace
COPY . /workspace

RUN ls /workspace && cat /workspace/pyproject.toml 2>/dev/null || cat /workspace/setup.py 2>/dev/null || cat /workspace/setup.cfg 2>/dev/null
RUN ls /workspace/tests/ | head -20 && pip install build-essential 2>/dev/null; apt-get install -y git build-essential curl ca-certificates -q 2>/dev/null; echo "done"
RUN pip install uv -q && echo "uv installed"
RUN cd /workspace && pip install uv_build -q 2>&1 | tail -5 && echo "done"
RUN cd /workspace && pip install -e . -q 2>&1 | tail -20
RUN python -c "import skfp; print('skfp imported successfully')" && pip install pytest pytest-rerunfailures -q 2>&1 | tail -5
RUN cd /workspace && python -m pytest --collect-only -q 2>&1 | tail -20
