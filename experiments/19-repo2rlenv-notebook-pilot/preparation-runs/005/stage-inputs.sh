# Stage the original input data for the Scanpy preprocessing & clustering
# reference run. Runs after dependency installation, with the virtual
# environment's python on PATH; network is available only here. Downloads the
# two 10X filtered feature matrices from figshare
# (doi:10.6084/m9.figshare.22716739.v1, NeurIPS 2021 benchmark dataset,
# CC BY 4.0), verifies them against the provider-supplied MD5 checksums and
# sizes, and writes a SHA-256 receipt to /work/setup-inputs.json.

set -eu

python - <<'PY'
import hashlib
import json
import sys
import urllib.request
from pathlib import Path

DEST_DIR = Path("/inputs")
DEST_DIR.mkdir(parents=True, exist_ok=True)

FILES = [
    {
        "url": "https://ndownloader.figshare.com/files/40347877",
        "name": "s1d1_filtered_feature_bc_matrix.h5",
        "md5": "a99285913ea3f3d22600d3d2f8a88e34",
        "bytes": 22848647,
    },
    {
        "url": "https://ndownloader.figshare.com/files/40347880",
        "name": "s1d3_filtered_feature_bc_matrix.h5",
        "md5": "825f7f7578e3dc0b8955f5a97a402338",
        "bytes": 20432298,
    },
]


def checksums(path):
    data = path.read_bytes()
    return data, hashlib.md5(data).hexdigest(), hashlib.sha256(data).hexdigest()


def verify_or_download(rec):
    dest = DEST_DIR / rec["name"]
    if dest.is_file():
        data, md5, _ = checksums(dest)
        if len(data) == rec["bytes"] and md5 == rec["md5"]:
            return dest
    tmp = dest.with_name(dest.name + ".part")
    print(f"Downloading {rec['name']} from {rec['url']} ...")
    request = urllib.request.Request(
        rec["url"], headers={"User-Agent": "reference-setup"}
    )
    try:
        with urllib.request.urlopen(request, timeout=600) as response, open(
            tmp, "wb"
        ) as fh:
            while True:
                chunk = response.read(1 << 20)
                if not chunk:
                    break
                fh.write(chunk)
        data, md5, _ = checksums(tmp)
        if len(data) != rec["bytes"]:
            sys.exit(
                f"{rec['name']}: size mismatch (expected {rec['bytes']}, got {len(data)})"
            )
        if md5 != rec["md5"]:
            sys.exit(
                f"{rec['name']}: MD5 mismatch (expected {rec['md5']}, got {md5})"
            )
        tmp.replace(dest)
    finally:
        if tmp.is_file():
            tmp.unlink()
    return dest


receipt = {"files": []}
for rec in FILES:
    dest = verify_or_download(rec)
    _, _, sha256 = checksums(dest)
    receipt["files"].append(
        {"local_path": str(dest), "source": rec["url"], "sha256": sha256}
    )

Path("/work/setup-inputs.json").write_text(json.dumps(receipt, indent=2) + "\n")
print(
    f"Staged {len(receipt['files'])} input files in /inputs; "
    "receipt written to /work/setup-inputs.json"
)
PY
