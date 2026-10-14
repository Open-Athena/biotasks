#!/bin/sh
# Reference environment + input staging for:
#   "Preprocessing and clustering" (scanpy basics tutorial)
#   scverse/scanpy @ 8c1463d5d97272d5811ad3f4efb57483e23b4c7e
#   docs/tutorials/basics/clustering.ipynb (BSD-3-Clause)
# Input data: NeurIPS 2021 openproblems benchmark bone marrow samples
#   (figshare DOI 10.6084/m9.figshare.22716739.v1, CC BY 4.0).
set -eu

mkdir -p /work /work/cache /work/run /work/outputs /inputs

# ---------------------------------------------------------------- python env
python -m venv /work/venv
/work/venv/bin/python -m pip install --no-input --upgrade pip setuptools wheel

# The source notebook declares no dependency versions. It requires scanpy >= 1.11
# so that sc.pp.scrublet lives in the main namespace and sc.tl.leiden accepts
# flavor="igraph" (n_iterations=2); igraph is needed for that Leiden flavor;
# pooch and anndata are imported directly by the script; umap-learn backs
# sc.pp.neighbors/sc.tl.umap; seaborn backs sc.pl.violin. The resolved set is
# frozen into /work/setup-inputs.json below.
/work/venv/bin/python -m pip install --no-input \
    "scanpy>=1.11,<2" \
    anndata \
    pooch \
    igraph \
    leidenalg \
    umap-learn \
    seaborn

# Import sanity check only (no scientific analysis is executed here).
/work/venv/bin/python -c "import scanpy as sc, anndata, pooch, igraph; print('scanpy', sc.__version__)"

# ---------------------------------------------------------------- input data
# Download the two input files from the figshare download endpoints registered
# for DOI 10.6084/m9.figshare.22716739.v1, verify the provider byte sizes and
# MD5 checksums, compute SHA-256, stage under /inputs and write
# /work/setup-inputs.json.
/work/venv/bin/python - <<'PYEOF'
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path
from urllib.request import Request, urlopen

INPUTS = [
    {
        "name": "s1d1_filtered_feature_bc_matrix.h5",
        "role": "10X Genomics filtered feature-barcode matrix (gene expression), sample s1d1, bone marrow mononuclear cells",
        "url": "https://ndownloader.figshare.com/files/40347877",
        "doi": "10.6084/m9.figshare.22716739.v1",
        "expected_bytes": 22848647,
        "expected_md5": "a99285913ea3f3d22600d3d2f8a88e34",
    },
    {
        "name": "s1d3_filtered_feature_bc_matrix.h5",
        "role": "10X Genomics filtered feature-barcode matrix (gene expression), sample s1d3, bone marrow mononuclear cells",
        "url": "https://ndownloader.figshare.com/files/40347880",
        "doi": "10.6084/m9.figshare.22716739.v1",
        "expected_bytes": 20432298,
        "expected_md5": "825f7f7578e3dc0b8955f5a97a402338",
    },
]


def digest(path):
    md5 = hashlib.md5()
    sha256 = hashlib.sha256()
    nbytes = 0
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            md5.update(chunk)
            sha256.update(chunk)
            nbytes += len(chunk)
    return nbytes, md5.hexdigest(), sha256.hexdigest()


def download(url, dest):
    last_error = None
    for attempt in range(5):
        try:
            request = Request(url, headers={"User-Agent": "reference-setup/1.0"})
            with urlopen(request, timeout=300) as response, open(dest, "wb") as out:
                while True:
                    chunk = response.read(1 << 20)
                    if not chunk:
                        break
                    out.write(chunk)
            return
        except Exception as error:  # retry transient network failures
            last_error = error
            time.sleep(min(30, 5 * (attempt + 1)))
    raise RuntimeError(f"download failed for {url}: {last_error}")


records = []
for spec in INPUTS:
    dest = Path("/inputs") / spec["name"]
    if not dest.exists():
        download(spec["url"], dest)
    nbytes, md5, sha256 = digest(dest)
    if nbytes != spec["expected_bytes"]:
        raise SystemExit(f"{dest}: byte size {nbytes} != expected {spec['expected_bytes']}")
    if md5 != spec["expected_md5"]:
        raise SystemExit(f"{dest}: md5 {md5} != provider md5 {spec['expected_md5']}")
    records.append(
        {
            **spec,
            "staged_path": str(dest),
            "bytes": nbytes,
            "md5": md5,
            "md5_verified": True,
            "sha256": sha256,
        }
    )

freeze = subprocess.run(
    ["/work/venv/bin/pip", "freeze"], check=True, capture_output=True, text=True
).stdout.splitlines()

report = {
    "notebook": {
        "title": "Scanpy: Preprocessing and clustering",
        "url": "https://github.com/scverse/scanpy/blob/8c1463d5d97272d5811ad3f4efb57483e23b4c7e/docs/tutorials/basics/clustering.ipynb",
        "source_revision": "8c1463d5d97272d5811ad3f4efb57483e23b4c7e",
        "source_sha256": "9716c6e512d26225b0c6269b49ee01399211ab60b96d523182d66592021000a6",
        "license": "BSD-3-Clause",
    },
    "data_source": {
        "doi": "10.6084/m9.figshare.22716739.v1",
        "title": "NeurIPS 2021 Benchmark dataset (openproblems)",
        "license": "CC BY 4.0",
        "metadata_url": "https://api.figshare.com/v2/articles/22716739/versions/1",
    },
    "inputs": records,
    "python_version": sys.version,
    "resolved_packages": freeze,
}

with open("/work/setup-inputs.json", "w") as fh:
    json.dump(report, fh, indent=2)
print(json.dumps(report["inputs"], indent=2))
PYEOF

echo "setup complete: /work/venv, /work/setup-inputs.json, inputs staged in /inputs"
