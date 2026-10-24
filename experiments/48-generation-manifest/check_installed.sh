#!/usr/bin/env bash
set -eu
experiment=$(cd "$(dirname "$0")" && pwd)
worktrees=$(cd "$experiment/../../.." && pwd)
check_id=${1:?provide a new proof id}
build_id=${2:?provide the completed wheel test id}
case "$check_id:$build_id" in *[!a-zA-Z0-9_:-]*|'') exit 2 ;; esac
python_bin=$experiment/local-scratch/$build_id/test_installed_distribution_co0/installed/bin/python
test -x "$python_bin"
logs=$experiment/local-checks/$check_id
mkdir "$logs"
exec 9>/tmp/exe-codex-local-heavy.lock
flock -n 9 || exit 75
export POLARS_MAX_THREADS=1 RAYON_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
python - <<'PY' > "$logs/admission.txt"
from pathlib import Path
load = float(Path('/proc/loadavg').read_text().split()[0])
mem = int(next(s.split()[1] for s in Path('/proc/meminfo').read_text().splitlines() if s.startswith('MemAvailable:'))) * 1024
assert load < 1.5 and mem >= 2.5 * 1024**3 and mem - 150 * 1024**2 >= 2 * 1024**3
print({'one_minute_load': load, 'mem_available_bytes': mem, 'estimated_peak_bytes': 150 * 1024**2})
PY
date -u +%FT%TZ > "$logs/start.txt"
set +e
/usr/bin/time -v -o "$logs/resources.txt" nice -n 10 ionice -c 2 -n 7 timeout 60 env -u PYTHONDONTWRITEBYTECODE -u PYTHONPATH "$python_bin" -I "$experiment/prove_installed.py" --generation "$worktrees/45/experiments/45-generation-handoff/inputs-private/generation-002" --baseline "$worktrees/45/experiments/45-generation-handoff/inputs-private/fresh-validation-002/prepared-local/handoff/prepared" --archive "$worktrees/31/experiments/31-historical-builds/inputs-private/upstream-package.tar.gz" --dependency "$worktrees/31/experiments/31-historical-builds/inputs-private/tomli_w-1.2.0-py3-none-any.whl" --output "$experiment/inputs-private/$check_id" > "$logs/output.txt" 2>&1
status=$?
if [ "$status" = 0 ] && [ ! -f "$experiment/inputs-private/$check_id/proof.json" ]; then
    status=1
    printf '%s\n' 'Successful process exit without final proof is incomplete.' >> "$logs/output.txt"
fi
date -u +%FT%TZ > "$logs/end.txt"
printf '%s\n' "$status" > "$logs/exit.txt"
cat "$logs/output.txt"
exit "$status"
