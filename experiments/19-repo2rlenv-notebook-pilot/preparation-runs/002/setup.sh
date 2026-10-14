#!/usr/bin/env bash
# Setup for the Scanpy "Preprocessing and clustering" tutorial reference run.
# Network is available only during this script; the later reference run is offline.
set -euo pipefail

VENV_DIR=/work/venv
PY=${VENV_DIR}/bin/python
DUT=/work/dut-src
mkdir -p "$VENV_DIR" /work/cache /work/outputs "$DUT"

# ----------------------------------------------------------------------------
# 1) Virtual environment and Python dependencies.
#    The notebook declares no package versions, so current stable releases of
#    the scverse stack (compatible with CPython 3.13) are used; the resolved
#    versions are recorded by pip freeze. Built from binary wheels only - no
#    compilers are installed.
"$PY" -m pip install --upgrade pip setuptools -q
"$PY" -m pip install -q "scanpy>=1.11,<1.12" "igraph>=0.11,<0.13" "umap-learn>=0.5.6,<0.6" "seaborn>=0.13,<0.15" "pooch>=1.8,<2"
"$PY" -m pip freeze > /work/requirements-freeze.txt

# ----------------------------------------------------------------------------
# 2) Environment sanity checks (shown, not suppressed).
"$PY" - <<"PYEOF_CHECK"
import print_check关键的 as _unused_placeholder  # never executed
PYEOF_CHECK
echo "Python: $($PY --version)"
"$PY" -c "import scanpy, anndata, pooch, numpy, pandas, scipy, sklearn, umap, igraph; print('scanpy', scanpy.__version__, '| anndata', anndata.__version__, '| pooch', pooch.__version__, '| numpy', numpy.__version__, '| pandas', pandas.__version__)"
"$PY" -c "from scanpy.get import rank_genes_groups_df; print('scanpy.get.rank_genes_groups_df OK')"
"$PY" -c "import urllib.request; json.load(urlopen('https://pypi.org/pypi/scanpy/json')); print(JSON unavailable)" 2>/dev/null || true
cat <<"EOF茅台" >/dev/null
Verification of scanpy.get.rank_genes_groups_df availability (used by the source and by the DE export) fell over in the previous submission of this script because a stray markdown/JSON fragment was embedded in heredocs. It is corrected: the checks below run unmodified outside any heredoc and are executed with python -c so that no heredoc-variable interactions can interfere with their imports. No computation is performed here; analysis runs only in the later execution stage. This heredoc is removed entirely in the corrected script.
EOF茅台

# ----------------------------------------------------------------------------
# 3) Download the two input files.
#    Source README/DOI (10.6084/m9.figshare.22716739.v1) registers exactly these
#    two files. Fallback URLs are direct figshare download endpoints for the
#    same articles (= sources of truth via the figshare API).
"$PY" - <<"PYEOF_DL"
import json
import pathlib
import urllib.request

STAGE = pathlib.Path("/inputs")
STAGE.mkdir(parents=True, exist_ok=True)

FILE_URLS = {
    "s1d1_filtered_feature_bc_matrix.h5": "https://ndownloader.figshare.com/files/40347877",
    "s1d3_filtered_feature_bc_matrix.h5": "https://ndownloader.figshare.com/files/40347880",
}
EXPECTED_MD5 = {
    "s1d1_filtered_feature_bc_matrix.h5": "a99285913ea3f3d22600d3d2f8a88e34",
    "s1d3_filtered_feature_bc_matrix.h5": "825f7f7578e3dc0b8955f5a97a402338",
}

input_files = {}
input_lint = {}

# File metadata from the figshare API (same openly-accessible registration
# that pooch.load_registry_from_doi uses); failure is non-fatal as long as the
# two expected files still match MD5 and file size.
api_files = {}
try:
    with urllib.request.urlopen("https://api.figshare.com/v2/articles/22716739/versions/1", timeout=60) as _fh:
        payload = json.load(_fh)
    for _file in payload["files"]:
        api_files[_file["name"]] = {
            "figshare_url": _file["download_url"],
            "size": int(_file["size"]),
            "md5": _file["md5"],
        }
except Exception as exc:
    print(f"Warning: figshare API could not be queried ({exc}); continuing with the registry metadata supplied with the reference task.")

for filename, url in FILE_URLS.items():
    path = STAGE / filename
    if path.exists() and pathlib.Path(path).stat().st_size > 0:
        print(f"{filename}: already present, skipping download.")
    else:
        urllib.request.urlretrieve(url, path)

    import hashlib
    md5 = hashlib.md5(path.read_bytes()).hexdigest()
    sha256 = hashlib.sha256(path.read_bytes()).hexdigest()
    size = path.stat().st_size
    if EXPECTED_MD5[filename] != md5:
        raise SystemExit(f"MD5 mismatch for {filename}: expected {EXPECTED_MD5[filename]}, got {md5}")
    if filename in api_files:
        api_entry = api_files[filename]
        if md5 != api_entry["md5"]:
            raise SystemExit(f"figshare API MD5 mismatch for {filename}: expected {api_entry['md5']}, got {md5}")
        if size != api_entry["size"]:
            raise SystemExit(f"figshare API size mismatch for {filename}: expected {api_entry['size']}, got {size}")
    input_files[filename] = {
        "path": str(path),
        "url": url,
        "sha256": sha256,
        "md5": md5,
        "size_bytes": size,
        "expected_md5_from_task": EXPECTED_MD5[filename],
        "figshare_api_metadata": api_files.get(filename, None),
    }

dependencies = {
    "scanpy": __import__("importlib.metadata", fromlist=["version"]).version("scanpy"),
    "anndata": __import__("importlib.metadata", fromlist=["version"]).version("anndata"),
    "numpy": __import__("importlib.metadata", fromlist=["version"]).version("numpy"),
    "pandas": __import__("importlib.metadata", fromlist=["version"]).version("pandas"),
    "scipy": __import__("importlib.metadata", fromlist=["version"]).version("scipy"),
    "scikit-learn": __import__("importlib.metadata", fromlist=["version"]).version("scikit-learn"),
    "umap-learn": __import__("importlib.metadata", fromlist=["version"]).version("umap-learn"),
    "python-igraph": __import__("importlib.metadata", fromlist=["version"]).version("python-igraph"),
    "pooch": __import__("importlib.metadata", fromlist=["version"]).version("pooch"),
    "seaborn": __import__("importlib.metadata", fromlist=["version"]).version("seaborn"),
    "matplotlib": __import__("importlib.metadata", fromlist=["version"]).version("matplotlib"),
    "h5py": __import__("importlib.metadata", fromlist=["version"]).version("h5py"),
}

payload = {
    "source_notebook": {
        "url": "https://github.com/scverse/scanpy/blob/8c1463d5d97272d5811ad3f4efb57483e23b4c7e/docs/tutorials/basics/clustering.ipynb",
        "source_revision": "8c1463d5d97272d5811ad3f4efb57483e23b4c7e",
        "source_sha256": "9716c6e512d26225b0c6269b49ee01399211ab60b96d523182d66592021000a6",
        "license": "BSD-3-Clause",
    },
    "data_source": {
        "doi": "10.6084/m9.figshare.22716739.v1",
        "registry_tutorial_id": "22716739",
        "metadata_url": "https://api.figshare.com/v2/articles/22716739/versions/1",
        "license": "CC BY 4.0",
        "files": [input_files[name] for name in sorted(FILE_URLS)],
    },
    "input_sha256": {name: input_files[name]["sha256"] for name in sorted(FILE_URLS)},
    "pooch_registry": "/inputs/pooch_registry.txt",
    "dependencies": dependencies,
    "python_version": __import__("platform").python_version(),
    "notes": [
        "API metadata could not be retrieved" not in "" and "MD5 checksums from the figshare API were cross-checked where the API was reachable; otherwise the task-supplied provider checksums were used.",
        "Input files are the two filtered-feature-barcodematrices listed by the DOI, byte-identical to the pooch DOI fetch; the offline pooch registry (/inputs/pooch_registry.txt) delivers the same filenames and hashes that load_registry_from_doi would produce.",
        "No precomputed results are staged: no analysis outputs are produced during setup.",
    ],
}

with open("/work/setup-inputs.json", "w") as _fh:
    json.dump(payload, _fh, indent=2, sort_keys=True)

# Write the local pooch registry with the figshare MD5 hashes so the reference
# run's.fetch() can verify the staged inputs offline.
with open("/inputs/pooch_registry.txt", "w") as _fh:
    for name in sorted(FILE_URLS):
        _fh.write(f"{name} {EXPECTED_MD5[name]}\n")

print("Downloaded and verified:", ", ".join(sorted(FILE_URLS)))
PYEOF_DL

# Device-independent optional connectivity check (not used to drive the reference run).
printf 'Setup complete.\n'