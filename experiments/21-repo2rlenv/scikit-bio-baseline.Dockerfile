FROM python:3.12.3-slim
ENV OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
RUN apt-get update && apt-get install -y --no-install-recommends git build-essential && rm -rf /var/lib/apt/lists/*
WORKDIR /workspace
RUN git init && git remote add origin https://github.com/scikit-bio/scikit-bio.git && git fetch --depth=1 origin bd05e60efb0e6398aa6dc1485832c80a1104511b && git checkout --detach FETCH_HEAD
RUN python -m pip install --no-cache-dir -e '.[test]' 'pytest==9.0.3'
RUN python -m pip freeze --all > /opt/baseline-freeze.txt
