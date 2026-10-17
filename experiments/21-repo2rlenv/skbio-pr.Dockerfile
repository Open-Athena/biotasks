FROM python:3.13.2-slim
ENV OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 POLARS_MAX_THREADS=1 RAYON_NUM_THREADS=1
RUN apt-get update && apt-get install -y --no-install-recommends git build-essential && rm -rf /var/lib/apt/lists/*
WORKDIR /workspace
RUN git init && git remote add origin https://github.com/scikit-bio/scikit-bio.git && git fetch --depth=1 origin 71286a24bddff66c82cb25a7ca13441aa13c2f2c && git checkout --detach FETCH_HEAD
RUN python -m pip install --no-cache-dir -e '.[test]' 'numpy==2.5.3' 'scipy==1.18.1' 'pandas==3.0.6' 'pytest==9.0.3'
RUN python -m pip freeze --all > /opt/baseline-freeze.txt
