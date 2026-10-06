FROM ubuntu:24.04
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends python3 python3-venv bash tmux ca-certificates && rm -rf /var/lib/apt/lists/*
COPY wheelhouse/ /opt/wheels/
RUN python3 -m venv /opt/venv && /opt/venv/bin/pip install --no-index --find-links /opt/wheels uv==0.10.11 && /opt/venv/bin/uv pip install --python /opt/venv/bin/python --no-index --find-links /opt/wheels numpy==2.2.6 pandas==2.2.3 scipy==1.15.3 scikit-learn==1.6.1 joblib==1.4.2
ENV PATH="/opt/venv/bin:$PATH" OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
WORKDIR /workspace
COPY data/ /workspace/data/
COPY models/ /workspace/models/
COPY reference/ /workspace/reference/
COPY CONTRACT.md /workspace/CONTRACT.md
RUN chmod -R a-w /workspace/data /workspace/models /workspace/reference /workspace/CONTRACT.md
