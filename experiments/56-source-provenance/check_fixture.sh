#!/usr/bin/env bash
set -eu
experiment=$(cd "$(dirname "$0")" && pwd)
logs=$experiment/local-checks/fixture-001
mkdir -p "$experiment/local-checks"
mkdir "$logs"
exec 9>/tmp/exe-codex-local-heavy.lock
flock -n 9 || exit 75
export POLARS_MAX_THREADS=1 RAYON_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1
export UV_CONCURRENT_BUILDS=1 UV_CONCURRENT_INSTALLS=1 UV_CONCURRENT_DOWNLOADS=1
export PATH="$experiment/../../../pipeline54/.venv/bin:$PATH"
python - <<'PY' > "$logs/admission.txt"
from pathlib import Path
load=float(Path('/proc/loadavg').read_text().split()[0])
mem=int(next(s.split()[1] for s in Path('/proc/meminfo').read_text().splitlines() if s.startswith('MemAvailable:')))*1024
assert load<1.5 and mem>=2.5*1024**3 and mem-200*1024**2>=2*1024**3
print({'load':load,'available_bytes':mem,'estimated_peak_bytes':200*1024**2})
PY
date -u +%FT%TZ > "$logs/start.txt"
set +e
/usr/bin/time -v -o "$logs/resources.txt" nice -n 10 ionice -c 2 -n 7 timeout 120 bash -c '
set -eu
experiment=$1
python -B "$experiment/prepare_fixture.py"
fixture=$experiment/inputs-private/local-probe-001
export TMPDIR="$fixture/tmp"
for project in release companion; do
    (cd "$fixture/$project" && uv build --offline --no-sources --wheel --out-dir "$fixture/wheels")
done
uv venv --python "$experiment/../../../pipeline54/.venv/bin/python" "$fixture/venv"
target_python=$fixture/venv/bin/python
uv pip install --offline --python "$target_python" uv_build==0.12.21
controller_python=/home/exedev/miniforge3/bin/python3.13
"$controller_python" -m pip --python "$target_python" --version > "$experiment/fixture-pip-version.txt"
"$controller_python" -m pip --python "$target_python" install --no-index --no-build-isolation --no-deps -e "$fixture/checkout"
"$target_python" -B "$experiment/collect.py" --checkout "$fixture/checkout" --project biotasks56-target --module biotasks56_target > "$experiment/editable-report.json"
"$controller_python" -m pip --python "$target_python" install --no-index --find-links "$fixture/wheels" "$fixture/wheels/biotasks56_companion-1.0.0-py3-none-any.whl"
"$target_python" -B "$experiment/collect.py" --checkout "$fixture/checkout" --project biotasks56-target --module biotasks56_target > "$experiment/replaced-report.json"
python - <<'"'"'PY'"'"' "$experiment"
import json,sys
from pathlib import Path
p=Path(sys.argv[1])
a=json.loads((p/'"'"'editable-report.json'"'"').read_text())
b=json.loads((p/'"'"'replaced-report.json'"'"').read_text())
assert a['"'"'binding'"'"']=='"'"'checkout'"'"' and a['"'"'distribution'"'"']['"'"'version'"'"']=='"'"'0.0.0'"'"'
assert b['"'"'binding'"'"']=='"'"'foreign'"'"' and b['"'"'distribution'"'"']['"'"'version'"'"']=='"'"'1.0.0'"'"'
assert a['"'"'distribution'"'"']['"'"'direct_url'"'"']['"'"'dir_info'"'"']['"'"'editable'"'"'] is True
print({'"'"'synthetic_actual_pip_mechanism_demonstrated'"'"':True,'"'"'anndata_mechanism_proven'"'"':False,'"'"'new_model_native_calls'"'"':0})
PY
' check "$experiment" > "$logs/output.txt" 2>&1
status=$?
date -u +%FT%TZ > "$logs/end.txt"
printf '%s\n' "$status" > "$logs/exit.txt"
tail -55 "$logs/output.txt"
exit "$status"
