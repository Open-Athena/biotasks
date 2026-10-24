"""Read-only provenance needed to exclude original workers from the trial."""
import argparse
import hashlib
import json
from pathlib import Path

from iris.cli.connect import connect_controller
from iris.client.client import IrisClient
from iris.cluster.types import JobName
from iris.resources.state import is_job_finished

ROOT = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', required=True, type=Path)
    parser.add_argument('--exclude-job', action='append', default=[])
    parser.add_argument('--receipt', action='append', type=Path, default=[])
    args = parser.parse_args()
    manifest = json.loads((ROOT/'cold-worker-inputs.json').read_text())
    jobs = [manifest['original_job_id'], *args.exclude_job]
    records = []
    if args.receipt:
        for path in args.receipt:
            data = path.read_bytes()
            value = json.loads(data)
            assert value['job_id'] in jobs and value.get('worker_id')
            records.append(dict(job_id=value['job_id'], state=value['state'], worker_ids=[value['worker_id']],
                provenance='Retained acknowledged submission; not a fresh runtime status observation',
                receipt_sha256=hashlib.sha256(data).hexdigest()))
        assert {r['job_id'] for r in records} == set(jobs) and len(records) == len(jobs)
    else:
        with connect_controller(config_file=args.config) as endpoint:
            with IrisClient.remote(endpoint.url, credentials=endpoint.credentials, timeout_ms=30000) as client:
                for name in jobs:
                    job = client.job(JobName.from_string(name))
                    state = job.status()
                    assert is_job_finished(state.state)
                    attempts = job.task(0).describe().status.attempts
                    assert attempts and all(a.worker_id for a in attempts)
                    records.append(dict(job_id=name, state=str(state.state), worker_ids=sorted({a.worker_id for a in attempts})))
    result = dict(jobs=records, excluded_worker_ids=sorted({worker for r in records for worker in r['worker_ids']}),
        purpose='Read-only original-worker exclusion; no submission or Docker operation', model_calls=0)
    assert all('-worker-' in w for w in result['excluded_worker_ids'])
    result['excluded_tpu_names'] = sorted({w.rsplit('-worker-', 1)[0] for w in result['excluded_worker_ids']})
    target = ROOT/'inputs-private/original-workers.json'
    assert not target.exists()
    target.write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(dict(source_jobs=len(records), excluded_worker_ids=len(result['excluded_worker_ids']), submitted=False)))


if __name__ == '__main__':
    main()
