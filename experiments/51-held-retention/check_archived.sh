#!/usr/bin/env bash
set -eu
cd "$(dirname "$0")/../.."
experiment=experiments/51-held-retention
phase=${1:?offline or publish}
case "$phase" in offline|publish) ;; *) exit 2 ;; esac
logs=$experiment/local-checks/archived-$phase-001
mkdir "$logs"
exec 9>/tmp/exe-codex-local-heavy.lock
flock -n 9 || exit 75
export POLARS_MAX_THREADS=1 RAYON_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1
python - <<'PY' > "$logs/admission.txt"
from pathlib import Path
load = float(Path('/proc/loadavg').read_text().split()[0])
mem = int(next(s.split()[1] for s in Path('/proc/meminfo').read_text().splitlines() if s.startswith('MemAvailable:'))) * 1024
assert load < 1.5 and mem >= 2.5 * 1024**3 and mem - 200 * 1024**2 >= 2 * 1024**3
print({'one_minute_load': load, 'mem_available_bytes': mem, 'estimated_peak_bytes': 200 * 1024**2})
PY
date -u +%FT%TZ > "$logs/start.txt"
set +e
/usr/bin/time -v -o "$logs/resources.txt" nice -n 10 ionice -c 2 -n 7 timeout 300 ../48/experiments/48-generation-manifest/inputs-private/candidate-runner/bin/python -B "$experiment/prove_archived.py" "$phase" \
    --original ../47/experiments/47-bootstrap-recipe-state/inputs-private/comparison-001/validation \
    --output "$experiment/inputs-private/archived-001" \
    --proof "$experiment/archived-$phase-proof.json" \
    --prefix research/51-held-retention \
    --reviewed-reference ../49/experiments/49-native-incomplete-retention/recovery-config.json > "$logs/output.txt" 2>&1
status=$?
date -u +%FT%TZ > "$logs/end.txt"
printf '%s\n' "$status" > "$logs/exit.txt"
cat "$logs/output.txt"
exit "$status"
