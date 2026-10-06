FROM python:3.12-slim

# Platform tooling: tmux for the agent shell, uv for isolated Python tool runs.
RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates curl tmux \
    && rm -rf /var/lib/apt/lists/* \
    && curl -LsSf https://astral.sh/uv/0.10.11/install.sh | sh \
    && rm -rf /var/lib/apt/lists/*

ENV PATH="/root/.local/bin:${PATH}"

# Pinned scientific environment on Python 3.12.
RUN pip install --no-cache-dir \
        numpy==2.3.3 \
        scipy==1.16.2 \
        pandas==2.3.3 \
        scikit-learn==1.7.2 \
        pytest==8.4.2

# Single-threaded numerics: one worker/thread throughout, for determinism.
ENV OMP_NUM_THREADS=1 \
    OPENBLAS_NUM_THREADS=1 \
    MKL_NUM_THREADS=1 \
    NUMEXPR_NUM_THREADS=1

WORKDIR /app

# Observed breast-cancer FNA cytopathology dataset, staged verbatim by the
# build (trailing-comma header artifact and identifier column are part of the
# raw file and are intentionally left in place).
COPY data/data.csv /app/data/data.csv

RUN python -c "import sys; assert sys.version_info[:2] == (3, 12), sys.version" \
    && python -c "import numpy, scipy, pandas, sklearn, pytest; print('numpy', numpy.__version__); print('scipy', scipy.__version__); print('pandas', pandas.__version__); print('sklearn', sklearn.__version__); print('pytest', pytest.__version__)"
