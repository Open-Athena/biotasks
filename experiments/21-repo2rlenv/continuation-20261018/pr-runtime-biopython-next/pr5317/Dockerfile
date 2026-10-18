FROM python:3.12.3-slim
ENV OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 POLARS_MAX_THREADS=1 RAYON_NUM_THREADS=1
RUN apt-get update && apt-get install -y --no-install-recommends git build-essential && rm -rf /var/lib/apt/lists/*
WORKDIR /workspace
RUN git init && git remote add origin https://github.com/biopython/biopython.git && git fetch --depth=1 origin 5bbc6c12c505301f2d681f932c30fdb8fcbe9a6e && git checkout --detach FETCH_HEAD
RUN python -m pip install --no-cache-dir -e . 'numpy==2.4.2' 'pytest==9.0.3'
RUN python -m pip freeze --all > /opt/baseline-freeze.txt
RUN mkdir -p /opt/biopython-baseline-extensions && find Bio BioSQL -type f -name "*.so" -exec cp --parents {} /opt/biopython-baseline-extensions/ \; && find /opt/biopython-baseline-extensions -type f -exec sha256sum {} \; > /opt/biopython-baseline-extension-sha256.txt
