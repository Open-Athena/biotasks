set -euo pipefail

mkdir -p /work /work/cache /work/outputs /inputs

python3 -m venv /work/venv
/work/venv/bin/python -m pip install --upgrade pip setuptools wheel
# The notebook declares no dependency versions; install the current stable scverse stack
# required by this tutorial (igraph+leidenalg for flavor="igraph", umap-learn for the
# UMAP step, pooch per the source imports). Resolved versions are recorded below.
/work/venv/bin/python -m pip install --no-cache-dir scanpy anndata pooch leidenalg igraph umap-learn

# Smoke-check the environment (not scientific analysis)
/work/venv/bin/python -c "import scanpy, anndata, pooch, igraph, leidenalg, umap, numpy, pandas, scipy, sklearn"

# Stage the two source input files and record identities plus SHA-256 checksums
/work/venv/bin/python - <<'PY'
import hashlib
import json
import os
import subprocess
import urllib.request

specs = [
    {
        "name": "s1d1_filtered_feature_bc_matrix.h5",
        "url": "https://ndownloader.figshare.com/files/40347877",
        "bytes": 22848647,
        "provider_md5": "a99285913ea3f3d22600d3d2f8a88e34",
    },
    {
        "name": "s1d3_filtered_feature_bc_matrix.h5",
        "url": "https://ndownloader.figshare.com/files/40347880",
        "bytes": 20432298,
        "provider_md5": "825f7f7578e3dc0b8955f5a97a402338",
    },
]

def digest(path, algo):
    h = hashlib.new(algo)
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()

os.makedirs("/inputs", exist_ok=True)
inputs = []
for spec in specs:
    path = os.path.join("/inputs", spec["name"])
    if not (os.path.exists(path) and digest(path, "md5") == spec["provider_md5"]):
        urllib.request.urlretrieve(spec["url"], path)
    assert digest(path, "md5") == spec["provider_md5"], path
    assert os.path.getsize(path) == spec["bytes"], path
    inputs.append(
        {
            **spec,
            "doi": "10.6084/m9.figshare.22716739.v1",
            "local_path": path,
            "sha256": digest(path, "sha256"),
            "provider_md5_verified": True,
        }
    )

freeze = subprocess.run(
    ["/work/venv/bin/pip", "freeze"], capture_output=True, text=True, check=True
).stdout.splitlines()
deps = dict(line.split("==", 1) for line in freeze if "==" in line)

record = {
    "source_notebook": "https://github.com/scverse/scanpy/blob/8c1463d5d97272d5811ad3f4efb57483e23b4c7e/docs/tutorials/basics/clustering.ipynb",
    "data_doi": "10.6084/m9.figshare.22716739.v1",
    "inputs": inputs,
    "resolved_dependencies": deps,
}
with open("/work/setup-inputs.json", "w") as f:
    json.dump(record, f, indent=2)
PY