#!/bin/sh
# Input staging for the scanpy "Preprocessing and clustering" tutorial.
# Runs with the resolved Python environment on PATH; network is available here.
#
# The source notebook obtains its two 10x matrix files through pooch with a DOI
# base url (doi:10.6084/m9.figshare.22716739.v1/):
#
#     EXAMPLE_DATA = pooch.create(path=pooch.os_cache("scverse_tutorials"),
#                                 base_url="doi:10.6084/m9.figshare.22716739.v1/")
#     EXAMPLE_DATA.load_registry_from_doi()     # network: figshare API
#     path = EXAMPLE_DATA.fetch(filename)       # network: figshare download
#
# Reference execution is offline, so this recipe stages, into one fixed cache
# directory (/work/cache/scverse_tutorials, the persistent cache root):
#
#   1. the two original dataset .h5 files, byte-identical to the provider's
#      copies (md5 and size verified against the figshare article metadata for
#      doi:10.6084/m9.figshare.22716739.v1), at the file names pooch's registry
#      uses for them, and
#   2. registry.txt, a pooch registry file holding one "<name> md5:<md5>" line
#      per dataset file -- the same registry contents that
#      Pooch.load_registry_from_doi() records from that same provider metadata,
#      which analysis.py loads with Pooch.load_registry().
#
# With those present, EXAMPLE_DATA.fetch() performs no network access: pooch
# hashes each cached file, matches it against the registry, and hands back the
# cached path, from which sc.read_10x_h5 reads the original dataset bytes.
set -eu

CACHE_ROOT=/work/cache/scverse_tutorials
mkdir -p "$CACHE_ROOT"

# Provider metadata for the dataset DOI, as published by the data repository and
# recorded in the reviewed source provenance (name, size, md5, download url).
# A copy already staged by the controller under /inputs is reused (and
# re-verified) before any download is attempted.
CACHE_DIR="$CACHE_ROOT" python3 - <<'PY'
import hashlib
import json
import os
import pathlib
import shutil
import sys

CACHE_DIR = pathlib.Path(os.environ["CACHE_DIR"])
PROVIDER_FILES = [
    {
        "name": "s1d1_filtered_feature_bc_matrix.h5",
        "bytes": 22848647,
        "provider_md5": "a99285913ea3f3d22600d3d2f8a88e34",
        "url": "https://ndownloader.figshare.com/files/40347877",
    },
    {
        "name": "s1d3_filtered_feature_bc_matrix.h5",
        "bytes": 20432298,
        "provider_md5": "825f7f7578e3dc0b8955f5a97a402338",
        "url": "https://ndownloader.figshare.com/files/40347880",
    },
]
DOI = "10.6084/m9.figshare.22716739.v1"
INTENDED = {f["name"] for f in PROVIDER_FILES}


def md5_of(path):
    h = hashlib.md5(usedforsecurity=False)
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def matches(path, meta):
    path = pathlib.Path(path)
    if not path.is_file() or path.stat().st_size != meta["bytes"]:
        return False
    return md5_of(path) == meta["provider_md5"]


registry_lines = []
for meta in PROVIDER_FILES:
    name, dest = meta["name"], CACHE_DIR / meta["name"]
    if not matches(dest, meta):
        staged = pathlib.Path("/inputs") / name
        if matches(staged, meta):
            # Controller-staged original input; copy it into the cache pooch reads.
            shutil.copyfile(staged, dest)
            print(f"stage-inputs: copied {name} from /inputs into the cache")
        else:
            # Otherwise fetch from the provider, then verify.
            print(f"stage-inputs: fetching {name} from {meta['url']}")
            import urllib.request

            tmp = CACHE_DIR / f".{name}.staging"
            with urllib.request.urlopen(
                urllib.request.Request(meta["url"], headers={"User-Agent": "pooch/1.9 (+https://github.com/fatiando/pooch)"}),
                timeout=600,
            ) as response, tmp.open("wb") as fh:
                while True:
                    chunk = response.read(1024 * 1024)
                    if not chunk:
                        break
                    fh.write(chunk)
            if not matches(tmp, meta):
                tmp.unlink()
                raise SystemExit(f"stage-inputs: {name} failed provider verification")
            tmp.replace(dest)
            print(f"stage-inputs: downloaded {name} from the provider")
    if not matches(dest, meta):
        raise SystemExit(f"stage-inputs: {name} could not be staged correctly")
    print(f"stage-inputs: staged {name} ({meta['bytes']} bytes, md5 {meta['provider_md5']} verified)")
    registry_lines.append(f"{name} md5:{meta['provider_md5']}")

registry = CACHE_DIR / "registry.txt"
registry.write_text("\n".join(registry_lines) + "\n")
print(f"stage-inputs: wrote {registry}")
print(f"stage-inputs: cache for {DOI}:")
for path in sorted(CACHE_DIR.iterdir()):
    print(f"  {path.name} {path.stat().st_size}")
PY

echo "stage-inputs: done"
