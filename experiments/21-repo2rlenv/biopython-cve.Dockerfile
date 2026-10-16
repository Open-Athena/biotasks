FROM python:3.12.3-slim
ENV OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 POLARS_MAX_THREADS=1 RAYON_NUM_THREADS=1
RUN apt-get update && apt-get install -y --no-install-recommends git build-essential && rm -rf /var/lib/apt/lists/*
WORKDIR /workspace
RUN git init && git remote add origin https://github.com/biopython/biopython.git && git fetch --depth=1 origin ead54d7b2cca66226681ee37e355f7aa783881f2 && git checkout --detach FETCH_HEAD
RUN python -m pip install --no-cache-dir -e . 'pytest==9.0.3'
RUN python -m pip freeze --all > /opt/baseline-freeze.txt
