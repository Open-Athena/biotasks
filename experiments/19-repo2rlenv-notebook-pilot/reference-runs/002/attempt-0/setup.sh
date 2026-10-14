#!/bin/sh
set -eu

mkdir -p /work/cache /inputs

python3 -m venv /work/venv
/work/venv/bin/pip install --upgrade pip
/work/venv/bin/pip install --no-input \
    "scanpy>=1.11,<1.12" "anndata" "pooch" "igraph" "leidenalg" \
    "umap-learn" "matplotlib" "numpy" "pandas" "scipy" "h5py"

/work/venv/bin/python - <<'PYEOF'
import hashlib
import json
import pathlib
import urllib.request

INPUTS = pathlib.Path("/inputs")
INPUTS.mkdir(parents=True, exist_ok=True)
CACHE = pathlib.Path("/work/cache")
CACHE.mkdir(parents=True, exist_ok=True)

EXPECTED = [
    {
        "name": "s1d1_filtered_feature_bc_matrix.h5",
        "url": "https://ndownloader.figshare.com/files/40347877",
        "bytes": 22848647,
        "sha256": "322c30a7a4905f7f113472442d4aa2c81a1ad736c86651f6c0b81e5b2ff94ac8",
        "provider_md5": "a99285913ea3f3d22600d3d2f8a88e34",
    },
    {
        "name": "s1d3_filtered_feature_bc_matrix.h5",
        "url": "https://ndownloader.figshare.com/files/40347880",
        "bytes": 20432298,
        "sha256": "ca40b287fac57ac2048f11f56f1b630c7c188718908fc217c6baf2e49bdb1982",
        "provider_md5": "825f7f757e3dc0b8955f5a97a402338",
    },
]

records = []
for item in EXPECTED:
    path = INPUTS / item["name"]
    downloaded = not path.is_file()
    if downloaded:
        req = urllib.request.Request(item["url"], headers={"User-Agent": "reference-setup"})
        with urllib.request.urlopen(req, timeout=600) as resp, open(path, "wb") as fh:
            while True:
                chunk = resp.read(1 << 20)
                if not chunk:
                    break
                fh.write(chunk)
    data = path.read_bytes()
    sha256 = hashlib.sha256(data).hexdigest()
    md5 = hashlib.md5(data).hexdigest()
    if sha256 != item["sha256"]:
        raise SystemExit("sha256 mismatch for %s: %s" % (item["name"], sha256))
    if md5 != item["provider_md5"]:
        raise SystemExit("provider md5 mismatch for %s: %s" % (item["name"], md5))
    if len(data) != item["bytes"]:
        raise SystemExit("size mismatch for %s" % item["name"])
    records.append({
        "name": item["name"],
        "url": item["url"],
        "local_path": str(path),
        "bytes": len(data),
        "sha256": sha256,
        "provider_md5": md5,
        "downloaded_in_setup": downloaded,
        "checksums_verified": True,
    })

import importlib.metadata as im

packages = ["scanpy", "anndata", "pooch", "igraph", "leidenalg", "umap-learn",
            "numba", "pynndescent", "numpy", "scipy", "pandas", "h5py", "matplotlib"]
versions = {}
for name in packages:
    try:
        versions[name] = im.version(name)
    except im.PackageNotFoundError:
        versions[name] = None

meta = {"error": None, "staged": False}
try:
    with urllib.request.urlopen("https://api.figshare.com/v2/articles/22716739/versions/1", timeout=120) as resp:
        raw = resp.read()
    (CACHE / "figshare_article_22716739_v1.json").write_bytes(raw)
    meta["staged"] = True
except Exception as exc:  # metadata staging is best-effort
    meta["error"] = str(exc)

with open("/work/setup-inputs.json", "w") as fh:
    json.dump({
        "data_source": {
            "doi": "10.6084/m9.figshare.22716739.v1",
            "license": "CC BY 4.0",
            "citation_dataset": "NeurIPS 2021 Multimodal Single-Cell Integration Challenge, bone marrow mononuclear cells (samples s1d1, s1d3)",
            "figshare_metadata_cached_at": "/work/cache/figshare_article_22716739_v1.json",
            "figshare_metadata": meta,
        },
        "inputs": records,
        "package_versions": versions,
        "python": __import__("platform").python_version(),
    }, fh, indent=2)

print(json.dumps({"inputs": records, "package_versions": versions}, indent=2))
PYEOF
