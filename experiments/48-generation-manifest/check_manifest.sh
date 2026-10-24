#!/usr/bin/env bash
set -eu
cd "$(dirname "$0")/../.."
experiment=experiments/48-generation-manifest
check_id=${1:?provide a unique check id}
case "$check_id" in *[!a-zA-Z0-9_-]*|'') exit 2 ;; esac
logs=$experiment/local-checks/$check_id
mkdir -p "$experiment/local-checks" "$experiment/local-scratch"
mkdir "$logs"
exec 9>/tmp/exe-codex-local-heavy.lock
flock -n 9 || exit 75
export POLARS_MAX_THREADS=1 RAYON_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1
python - <<'PY' > "$logs/admission.txt"
from pathlib import Path
load = float(Path('/proc/loadavg').read_text().split()[0])
mem = int(next(s.split()[1] for s in Path('/proc/meminfo').read_text().splitlines() if s.startswith('MemAvailable:'))) * 1024
assert load < 1.5 and mem >= 2.5 * 1024**3 and mem - 150 * 1024**2 >= 2 * 1024**3
print({'one_minute_load': load, 'mem_available_bytes': mem, 'estimated_peak_bytes': 150 * 1024**2})
PY
date -u +%FT%TZ > "$logs/start.txt"
set +e
/usr/bin/time -v -o "$logs/resources.txt" nice -n 10 ionice -c 2 -n 7 timeout 60 /home/exedev/.codex/worktrees/8ea0/biotasks/.research-worktrees/pipeline44-final/.venv/bin/python -B -m pytest -q "$experiment/test_manifest_flow.py" --basetemp "$experiment/local-scratch/$check_id" > "$logs/output.txt" 2>&1
status=$?
date -u +%FT%TZ > "$logs/end.txt"
printf '%s\n' "$status" > "$logs/exit.txt"
cat "$logs/output.txt"
exit "$status"
