#!/bin/sh
# Stage the original inputs for the PyRadiomics RadiomicsExample notebook.
#
# The analysis reads its inputs through two path conventions of the notebook,
# both of which must be satisfied offline:
#
# 1. radiomics.getTestCase('brain1'/'brain2') looks for
#    <tempdir>/pyradiomics/data/<case>_image.nrrd and <case>_label.nrrd
#    before ever attempting a network download. The master copies of the two
#    brain test cases are staged under /work/cache/pyradiomics/data (these are
#    the files recorded in inputs.json) and the tempdir location that
#    getTestCase() consults is linked to them.
#
# 2. Params.yaml is read through the relative path
#    os.path.join(os.getcwd(), '..', 'examples', 'exampleSettings', 'Params.yaml')
#    The scientific run uses /work/run as working directory, so the file must
#    exist at /work/examples/exampleSettings/Params.yaml, i.e. one level above
#    the working directory - the same position relative to the notebook inside
#    the pyradiomics source repository.
#
# All data is re-fetched from its recorded source on each staging run; nothing
# from exploratory shell work is reused.

set -eu

CACHE=/work/cache
DATA_DIR="$CACHE/pyradiomics/data"
PARAMS_DIR=/work/examples/exampleSettings

mkdir -p "$CACHE" "$DATA_DIR" "$PARAMS_DIR"

# --- retrieve the pyradiomics 3.1.0 source tree --------------------------------
# The PyPI sdist of the release matching the notebook's source revision ships
# both the data/ test cases and the examples/exampleSettings parameter file.
SDIST_URL='https://files.pythonhosted.org/packages/03/c1/20fc2c50ab1e3304da36d866042a1905a2b05a1431ece35448ab6b4578f2/pyradiomics-3.1.0.tar.gz'
SDIST_FILE=$CACHE/pyradiomics-3.1.0.tar.gz

if [ ! -f "$SDIST_FILE" ]; then
  echo "[stage] downloading pyradiomics 3.1.0 sdist"
  python3 - "$SDIST_URL" "$SDIST_FILE" <<'PY'
import sys, urllib.request
url, dest = sys.argv[1], sys.argv[2]
urllib.request.urlretrieve(url, dest)
print("[stage] saved", dest)
PY
fi

SRC_ROOT=$CACHE/pyradiomics-3.1.0-source
if [ ! -f "$SRC_ROOT/data/brain1_image.nrrd" ]; then
  echo "[stage] unpacking sdist"
  rm -rf "$SRC_ROOT"
  mkdir -p "$SRC_ROOT"
  tar -xzf "$SDIST_FILE" -C "$SRC_ROOT" --strip-components=1
fi

# --- 1. brain1/brain2 test cases ----------------------------------------------
for f in brain1_image.nrrd brain1_label.nrrd brain2_image.nrrd brain2_label.nrrd; do
  if [ ! -f "$DATA_DIR/$f" ]; then
    cp "$SRC_ROOT/data/$f" "$DATA_DIR/$f"
    echo "[stage] staged $DATA_DIR/$f"
  fi
done

# Point the getTestCase() default data directory at the staged copies.
# tempfile.gettempdir() honours TMPDIR/TEMP/TMP when set and otherwise falls
# back to /tmp. Cover every candidate root the run could resolve to. This is
# pure path plumbing: the bytes the analysis reads are the tracked files in
# /work/cache/pyradiomics/data, and getTestCase() only downloads when one of
# those files is missing.
for root in "${TMPDIR:-}" "${TEMP:-}" "${TMP:-}" /tmp /var/tmp /usr/tmp; do
  [ -n "$root" ] || continue
  pyrad_link="$root/pyradiomics/data"
  if [ "$(readlink "$pyrad_link" 2>/dev/null || true)" != "$DATA_DIR" ]; then
    mkdir -p "$root/pyradiomics"
    rm -rf "$pyrad_link"
    ln -s "$DATA_DIR" "$pyrad_link"
    echo "[stage] linked $pyrad_link -> $DATA_DIR"
  fi
done

# --- 2. Params.yaml -------------------------------------------------------------
if [ ! -f "$PARAMS_DIR/Params.yaml" ]; then
  cp "$SRC_ROOT/examples/exampleSettings/Params.yaml" "$PARAMS_DIR/Params.yaml"
  echo "[stage] staged $PARAMS_DIR/Params.yaml"
fi

echo "[stage] done"
