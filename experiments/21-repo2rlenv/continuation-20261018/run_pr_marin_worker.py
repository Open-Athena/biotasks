"""Run a frozen native PR correctness-control cohort in one authorized Daytona sandbox."""
import argparse
import hashlib
import json
import signal
from pathlib import Path

from repo2rlenv.campaigns.budget import BudgetLedger
from repo2rlenv.execution.base import WorkerSpec
from repo2rlenv.execution.lifecycle import prepare_docker, provision_worker, save_record, stop_worker

SOURCE_SHA256 = '7e387fbb04d5374964de37a31b63e6cabc310198703213c6a40bf8d5c6dd4755'


def deadline(signum, frame):
    raise TimeoutError('Native PR cohort execution deadline reached')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--campaign', type=Path, required=True)
    parser.add_argument('--worker-name', required=True)
    parser.add_argument('--source-archive', type=Path, required=True)
    parser.add_argument('--inputs-archive', type=Path, required=True)
    parser.add_argument('--inputs-sha256', required=True)
    parser.add_argument('--timeout-sec', type=int, required=True)
    args = parser.parse_args()
    if not 60 <= args.timeout_sec <= 7200:
        parser.error('Execution timeout must be 60..7200 seconds')
    for file, expected in [(args.source_archive, SOURCE_SHA256), (args.inputs_archive, args.inputs_sha256)]:
        with file.open('rb') as stream:
            if hashlib.file_digest(stream, 'sha256').hexdigest() != expected:
                raise ValueError('Frozen source/input archive changed')
    args.campaign.mkdir(parents=True, exist_ok=False)
    ledger = BudgetLedger(args.campaign / 'budget.sqlite', limit_usd='5')
    spec = WorkerSpec(provider='daytona', cpus=2, memory_mb=4096, disk_gb=10, timeout_sec=args.timeout_sec, name=args.worker_name)
    record = {'stage': 'native_Marin_correctness_parity_not_Atlas_admission', 'model_calls': 0, 'status': 'starting', 'execution_timeout_sec': args.timeout_sec, 'inputs_sha256': args.inputs_sha256}
    worker = None
    for sig in (signal.SIGTERM, signal.SIGINT, signal.SIGALRM):
        signal.signal(sig, deadline)
    signal.alarm(args.timeout_sec)
    try:
        worker, receipt = provision_worker(spec, args.campaign / 'workers', ledger, reserve_usd='5')
        prepare_docker(worker)
        worker.exec(['mkdir', '-p', '/work/native', '/evidence/native'], timeout=30).checked('mkdir')
        worker.upload(args.source_archive, '/work/native/source.tar.gz')
        worker.upload(args.inputs_archive, '/work/native/inputs.tar.gz')
        worker.upload(Path('run_pr_marin_parity.py'), '/work/native/run_pr_marin_parity.py')
        worker.upload(Path('check_pr_marin_parity.py'), '/work/native/check_pr_marin_parity.py')
        setup = worker.exec(['sh', '-c', 'set -eu; cd /work/native; tar -xzf source.tar.gz; mkdir inputs; tar -xzf inputs.tar.gz -C inputs; uv sync --frozen --no-dev --extra mutation --extra harbor --python 3.12.3 --project huggingface-Repo2RLEnv-27d04ee >/evidence/native/setup.log 2>&1'], timeout=600)
        record['setup_returncode'] = setup.returncode
        setup.checked('locked runtime install')
        run = worker.exec(['sh', '-c', 'export REPO2RLENV_REMOTE_WORKER=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 RAYON_NUM_THREADS=1 POLARS_MAX_THREADS=1; /work/native/huggingface-Repo2RLEnv-27d04ee/.venv/bin/python /work/native/run_pr_marin_parity.py --inputs /work/native/inputs --output /evidence/native/marin-parity >/evidence/native/worker.log 2>&1; code=$?; printf "%s\\n" "$code" >/evidence/native/worker-exit.txt; exit "$code"'], timeout=min(6000, args.timeout_sec))
        record.update(worker_returncode=run.returncode, status='cohort_process_completed' if run.returncode == 0 else 'cohort_process_failed')
    except BaseException as exc:
        record.update(status='failed', error_type=type(exc).__name__)
        raise
    finally:
        signal.alarm(0)
        save_record(args.campaign / 'result.json', record)
        if worker is not None:
            try:
                packed = worker.exec(['sh', '-c', 'tar -czf /work/native-evidence.tar.gz -C /evidence native && stat -c %s /work/native-evidence.tar.gz'], timeout=120)
                packed.checked('preserve partial native evidence')
                size = int(packed.stdout.strip())
                if size > 128 * 1024**2:
                    raise ValueError('Native evidence exceeds frozen capture bound')
                worker.download('/work/native-evidence.tar.gz', args.campaign / 'native-evidence.tar.gz')
                record['evidence_bytes'] = size
            finally:
                record['cleanup'] = stop_worker(receipt, ledger)['state']
                save_record(args.campaign / 'result.json', record)


if __name__ == '__main__':
    main()
