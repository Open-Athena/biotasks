"""Audit original execution/accounting evidence and query the same terminal handles."""

import argparse
import datetime
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import subprocess
import tarfile

from iris.cli.connect import connect_controller
from iris.client.client import IrisClient
from iris.cluster.types import JobName
from iris.resources.state import is_job_finished

ROOT = Path(__file__).resolve().parent


def read(path):
    return json.loads(path.read_text())


def sha(path):
    with path.open('rb') as handle:
        return hashlib.file_digest(handle, 'sha256').hexdigest()


def stamp(value):
    return datetime.datetime.fromisoformat(value.removeprefix('Timestamp(').removesuffix(')'))


def phase_records(path):
    events, billing = [], None
    expanded = 0
    with tarfile.open(path, 'r|gz') as archive:
        for member in archive:
            expanded += member.size
            assert expanded < 512 * 1024**2
            if member.name == 'native-observations/events.jsonl':
                assert member.isfile() and member.size < 10 * 1024**2
                events = [json.loads(line) for line in archive.extractfile(member) if line.strip()]
            elif member.name == 'native-observations/billing.json':
                assert member.isfile() and member.size < 10000
                billing = json.load(archive.extractfile(member))
    assert billing and billing['cost_complete']
    return events, billing


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--state-dir', type=Path, required=True)
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    cohort, pins, checkpoint = (read(ROOT / name) for name in
        ['cohort.json', 'pins.json', 'input-checkpoint.json'])
    assert len(cohort) == 10
    for relative, expected in checkpoint['payload_files'].items():
        assert sha(ROOT / relative) == expected['sha256'], relative
    for relative in ['submit.py', 'cohort.json']:
        path = ROOT / relative
        original = subprocess.check_output(['git', 'show', checkpoint['checkpoint_commit']
            + ':' + str(path.relative_to(ROOT.parents[1]))])
        assert path.read_bytes() == original
    adaptation = read(ROOT / 'reserved-worker-adaptation.json')
    original_submitter = (ROOT / 'submit.py').read_bytes()
    current_submitter = (ROOT / 'submit_current_reserved.py').read_bytes()
    assert hashlib.sha256(original_submitter).hexdigest() == adaptation['original_sha256']
    assert hashlib.sha256(current_submitter).hexdigest() == adaptation['prepared_sha256']
    assert current_submitter == original_submitter.replace(
        adaptation['only_byte_change']['from'].encode(), adaptation['only_byte_change']['to'].encode())
    assert adaptation['stage'] == 'proceed_under_existing_reserved_cpu_authorization_after_user_steering'
    final_submission = read(ROOT / 'results/OHIF__Viewers-submission-provenance.json')
    assert final_submission['run_id'] == 'biotasks28-ohif-viewers-001'
    assert final_submission['submitter_sha256'] == adaptation['prepared_sha256']
    assert final_submission['selected_existing_reserved_worker_healthy_clean']
    assert final_submission['selected_worker_base_commit'] == 'c7c14a252d'
    assert final_submission['first_submission'] and final_submission['new_capacity'] is False
    # No partial audit may silently declare the fixed cohort complete.
    for row in cohort:
        run = 'biotasks28-' + row['slug'].lower().replace('__', '-') + '-001'
        assert (args.state_dir / (run + '-terminal.json')).is_file(), run
    total_cost = Decimal('0')
    cpu_hours = Decimal('0')
    previous_finish = None
    reports = []
    with connect_controller(config_file=args.config) as endpoint:
        with IrisClient.remote(endpoint.url, credentials=endpoint.credentials, timeout_ms=30000) as client:
            for selected in cohort:
                run = 'biotasks28-' + selected['slug'].lower().replace('__', '-') + '-001'
                record = read(args.state_dir / (run + '-terminal.json'))
                receipt = read(args.state_dir / (run + '-receipt.json'))
                result = args.state_dir / (run + '-results')
                assert record['readback_verified'] and record['supervisor']['cleanup']['verified_empty']
                assert record['billing']['cost_complete'] and not record['billing']['unresolved_calls']
                assert receipt['job_id'] == '/exedev/' + run
                assert receipt['cpu'] == 4 and receipt['timeout_seconds'] == pins['job_timeout_seconds']
                assert len(record['attempts']) == 1
                attempt = record['attempts'][0]
                assert attempt['worker_id'] == receipt['worker_id']
                start, finish = stamp(attempt['started_at']), stamp(attempt['finished_at'])
                assert finish >= start and (previous_finish is None or start >= previous_finish)
                duration = finish - start
                micros = (duration.days * 86400 + duration.seconds) * 1000000 + duration.microseconds
                assert Decimal(micros) / 1000000 <= pins['job_timeout_seconds']
                allocated = Decimal(micros) * 4 / 3600000000
                cpu_hours += allocated
                previous_finish = finish
                manifest_path = ROOT / 'archives' / (selected['slug'] + '-manifest.json')
                manifest = read(manifest_path)
                published = read(ROOT / 'archives' / (selected['slug'] + '-receipt.json'))
                assert published['anonymous_download_verified'] and sha(manifest_path) == published['manifest_sha256']
                original_phase = next(item for item in manifest['files'] if item['path'] == 'evidence/phase-artifacts.tar.gz')
                assert sha(result / 'phase-artifacts.tar.gz') == original_phase['sha256']
                events, billing = phase_records(result / 'phase-artifacts.tar.gz')
                pending, calls, charged = set(), set(), set()
                actual = Decimal('0')
                config = read(ROOT / 'native-configs' / (selected['slug'] + '.json'))
                assert config['llm']['fallback'] is None
                for event in events:
                    if event['event'] == 'model_request':
                        assert not pending and actual < Decimal(str(pins['actual_model_stop_threshold_usd']))
                        assert event['call'] not in calls
                        assert event['model'] == config['llm']['provider'] + '/' + config['llm']['model']
                        assert event['max_tokens'] == 2048 and event['temperature'] == 0.2
                        pending.add(event['call']); calls.add(event['call'])
                    elif event['event'] == 'model_charge':
                        assert event['call'] in pending and event['call'] not in charged
                        charge = Decimal(event['actual_cost_usd'])
                        assert charge.is_finite() and charge >= 0
                        actual += charge
                        assert actual == Decimal(event['cumulative_actual_usd'])
                        pending.remove(event['call']); charged.add(event['call'])
                assert not pending and calls == charged and len(calls) <= config['bootstrap']['max_iterations']
                assert len(calls) == billing['model_calls'] == record['billing']['model_calls']
                assert actual == Decimal(billing['actual_cost_usd']) == Decimal(record['billing']['actual_cost_usd'])
                assert total_cost < Decimal(str(pins['aggregate_actual_model_stop_threshold_usd']))
                total_cost += actual
                unchanged = read(result / 'fresh-task-files-unchanged.json')
                assert unchanged['verified'] and unchanged['before'] == unchanged['after']
                for original_root, files in unchanged['before'].items():
                    task = result / 'expanded' / Path(original_root).relative_to('/work')
                    for relative, expected in files.items():
                        assert sha(task / relative) == expected
                controls = read(result / 'fresh-controls.json')
                assert len({(item['task'], item['agent']) for item in controls}) == len(controls)
                for item in controls:
                    if 'command' not in item:
                        assert item['state'] == 'unstarted'
                        continue
                    command = item['command']
                    for flag, expected in [('-a', item['agent']), ('-n', '1'), ('-k', '1'),
                            ('-r', '0'), ('--override-cpus', '1'), ('--override-memory-mb', '6144')]:
                        assert command[command.index(flag) + 1] == expected
                    assert item['agent'] in ['nop', 'oracle'] and '--verifier-timeout-multiplier' not in command
                job = client.job(JobName.from_string(receipt['job_id']))
                state = job.status().state
                live = job.task(0).describe()
                assert is_job_finished(state) and state.name == record['state']
                assert len(live.status.attempts) == 1
                assert live.resources.cpu_millicores == 4000 and live.resources.memory_bytes == 16 * 1024**3
                assert live.resources.disk_bytes == 30 * 1024**3 and live.resources.device is None
                reports.append({'repo': selected['repo'], 'run_id': run, 'live_state': state.name,
                    'original_attempts': 1, 'model_requests': len(calls), 'actual_cost_usd': str(actual),
                    'allocated_cpu_hours': str(allocated), 'started_at': str(start), 'finished_at': str(finish),
                    'controls_reached': sum(item['state'] != 'unstarted' for item in controls),
                    'controls_unstarted': sum(item['state'] == 'unstarted' for item in controls),
                    'actual_task_hashes_match_before_and_after': True, 'owned_cleanup_verified_empty': True,
                    'live_resources': {'cpu': 4, 'memory_gib': 16, 'disk_gib': 30, 'accelerator': None}})
                print(json.dumps(reports[-1]), flush=True)
    assert cpu_hours <= Decimal(str(pins['aggregate_allocated_cpu_hour_ceiling']))
    summary = read(ROOT / 'cohort-summary.json')
    assert total_cost == Decimal(summary['known_reported_actual_cost_usd'])
    assert abs(cpu_hours - Decimal(summary['reported_allocated_cpu_hours'])) < Decimal('0.00000001')
    output = {'checked_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'scope': 'Original-source, actual-charge, serial-budget, task-file and original-handle audit only; scientific reward audit, final archive readback, issue closure and local cleanup are separate requirements.',
        'input_checkpoint': checkpoint['checkpoint_commit'], 'all_ten_original_runs_accounted_for': True,
        'last_repository_worker_gate_adaptation': final_submission,
        'actual_cost_usd': str(total_cost), 'allocated_cpu_hours': str(cpu_hours), 'repositories': reports}
    args.output.write_text(json.dumps(output, indent=2) + '\n')
    print(json.dumps({k: v for k, v in output.items() if k != 'repositories'}, indent=2), flush=True)


if __name__ == '__main__':
    main()
