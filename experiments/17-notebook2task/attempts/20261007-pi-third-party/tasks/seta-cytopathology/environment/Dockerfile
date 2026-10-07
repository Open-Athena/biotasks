FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y build-essential git curl tmux && \
    rm -rf /var/lib/apt/lists/*

# Pre-install uv
RUN curl -LsSf https://astral.sh/uv/0.10.11/install.sh | sh
ENV PATH="/root/.local/bin:$PATH"

# Install Python ML packages
RUN uv pip install --system pandas numpy scikit-learn xgboost lightgbm matplotlib seaborn

# Set up dataset
RUN mkdir -p /data/breast-cancer-wisconsin /results
COPY data.csv /data/breast-cancer-wisconsin/data.csv
