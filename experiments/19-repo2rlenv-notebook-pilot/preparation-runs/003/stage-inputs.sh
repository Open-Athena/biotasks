#!/bin/sh
# Stage the two original 10x Genomics filtered feature-barcode matrices used by
# the scanpy "Preprocessing and clustering" tutorial (bone marrow mononuclear
# cells, NeurIPS 2021 benchmark, figshare DOI 10.6084/m9.figshare.22716739.v1).
# Downloads run while network is available, each file is verified against the
# provider MD5 and byte size from the figshare metadata, and identities plus
# SHA-256 checksums are recorded in /work/setup-inputs.json. The offline
# reference run loads these files from /inputs.
set -eu

mkdir -p /inputs /work/cache

python - <<'PYEOF'
import hashlib
import json
import pathlib
import sys
import time
import urllib.request

INPUTS = pathlib.Path("/inputs")

FILES = [
    {
        "url": "https://ndownloader.figshare.com/files/40347877",
        "name": "s1d1_filtered_feature_bc_matrix.h5",
        "provider_md5": "a99285913ea3f3d22600d3d2f8a88e34",
        "provider_bytes": 22848647,
    },
    {
        "url": "https://ndownloader.figshare.com/files/40347880",
        "name": "s1d3_filtered_feature_bc_matrix.h5",
        "provider_md5": "825f7f7578e3dc0b8955f5a97a402338",
        "provider_bytes": 20432298,
    },
]


def file_md5(path):
    digest = hashlib.md5()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def file_sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def download(url, dest):
    tmp = dest.with_name(dest.name + ".part")
    last_error = None
    for attempt in range(1, 4):
        try:
            request = urllib.request.Request(
                url, headers={"User-Agent": "reference-input-staging"}
            )
            with urllib.request.urlopen(request, timeout=120) as response, tmp.open(
                "wb"
            ) as handle:
                while True:
                    block = response.read(1024 * 1024)
                    if not block:
                        break
                    handle.write(block)
            tmp.replace(dest)
            return
        except Exception as error:
            last_error = error
            print(
                "download attempt %d for %s failed: %s" % (attempt, url, error),
                file=sys.stderr,
            )
            if tmp.exists():
                tmp.unlink()
            time.sleep(5)
    raise SystemExit("failed to download %s: %s" % (url, last_error))


records = []
for spec in FILES:
    dest = INPUTS / spec["name"]
    if not dest.is_file() or file_md5(dest) != spec["provider_md5"]:
        download(spec["url"], dest)
    observed_md5 = file_md5(dest)
    if observed_md5 != spec["provider_md5"]:
        raise SystemExit(
            "MD5 mismatch for %s: expected %s, got %s"
            % (dest, spec["provider_md5"], observed_md5)
        )
    observed_bytes = dest.stat().st_size
    if observed_bytes != spec["provider_bytes"]:
        raise SystemExit(
            "size mismatch for %s: expected %d, got %d"
            % (dest, spec["provider_bytes"], observed_bytes)
        )
    records.append(
        {
            "local_path": str(dest),
            "source": spec["url"],
            "sha256": file_sha256(dest),
        }
    )

receipt = {"files": records}
receipt_path = pathlib.Path("/work/setup-inputs.json")
receipt_path.write_text(json.dumps(receipt, indent=2) + "\n")
print(json.dumps(receipt, indent=2))
PYEOF
