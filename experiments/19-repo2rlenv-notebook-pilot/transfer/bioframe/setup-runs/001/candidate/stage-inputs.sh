#!/bin/sh
# Stage the three original input files used by the tutorial:
#   - ENCODE CTCF ChIP-seq peaks for HFF (ENCFF401MQL, narrowPeak, GRCh38)
#   - ENCODE blacklist regions (ENCFF356LFX, bed3, GRCh38)
#   - JASPAR CTCF motif UCSC track (MA0139.1, hg38, 2022 release)
# Files are downloaded from their original providers and verified against the
# provider-published md5 / byte sizes; the JASPAR server publishes no md5, so
# the expected size (and an md5 recorded from this exact download during setup)
# are used as integrity checks. The staged bytes must equal the ones the
# original notebook reads from the same URLs.
set -eu

DEST=/inputs
mkdir -p "$DEST"

python3 - "$DEST" <<'PY'
import hashlib
import sys
import time
import urllib.request
import urllib.error

dest = sys.argv[1]

expected = [
    # url, filename, expected bytes, expected md5 (None = size check only)
    (
        "https://www.encodeproject.org/files/ENCFF401MQL/@@download/ENCFF401MQL.bed.gz",
        "ENCFF401MQL.bed.gz",
        649474,
        "9dabac96e36309ed65dc1cb289c51079",
    ),
    (
        "https://www.encodeproject.org/files/ENCFF356LFX/@@download/ENCFF356LFX.bed.gz",
        "ENCFF356LFX.bed.gz",
        8211,
        "393688b4f06c9ce26165d47433dd8c37",
    ),
    (
        "http://expdata.cmmt.ubc.ca/JASPAR/downloads/UCSC_tracks/2022/hg38/MA0139.1.tsv.gz",
        "MA0139.1.tsv.gz",
        7698065,
        "0ebb58260d8ef79496390bec7266b503",
    ),
]

for url, name, size, md5 in expected:
    target = f"{dest}/{name}"
    last_err = None
    for attempt in range(4):
        try:
            urllib.request.urlretrieve(url, target)
            break
        except Exception as exc:  # noqa: BLE001
            last_err = exc
            time.sleep(3 * (attempt + 1))
    else:
        raise SystemExit(f"failed to download {name}: {last_err!r}")

    data = open(target, "rb").read()
    if len(data) != size:
        raise SystemExit(
            f"{name}: size {len(data)} != expected {size} -- aborting"
        )
    digest = hashlib.md5(data).hexdigest()
    if md5 is not None and digest != md5:
        raise SystemExit(f"{name}: md5 {digest} != expected {md5} -- aborting")
    print(f"staged {name}: {len(data)} bytes, md5 {digest}")
PY
