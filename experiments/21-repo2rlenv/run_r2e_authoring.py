"""Remote R2E authoring with explicit GLM adaptation and retained native bounds."""
import argparse
import dataclasses
import json
import os
import signal
import tarfile
from pathlib import Path

from glm_authoring_adapter import adapted_authoring
from repo2rlenv.campaigns.budget import BudgetLedger
from repo2rlenv.execution.artifacts import check_runtime_wheel
from repo2rlenv.execution.base import WorkerSpec
from repo2rlenv.execution.lifecycle import provision_worker, save_record, stop_worker
from repo2rlenv.pipelines.recipes.r2e.pipeline import R2EPipeline
from repo2rlenv.spec.input import GenerationInput
from repo2rlenv.spec.recipe_options import R2EOptions


def deadline(signum, frame):
    raise TimeoutError('R2E controller deadline')


def capture(campaign, destination):
    """Private recovery archive, streamed and bounded; never follow source links."""
    if destination.resolve().is_relative_to(campaign.resolve()):
        raise ValueError('Recovery destination must be outside campaign')
    total = 0
    members = []
    for path in sorted(campaign.rglob('*')):
        if path.is_symlink():
            # Preserve link metadata, never the target's contents. Extraction
            # and public eligibility are separately checked during recovery.
            members.append(path)
        elif path.is_file():
            total += path.stat().st_size
            if total > 512 * 1024**2:
                raise ValueError('Recovery archive exceeds 512 MiB input bound')
            members.append(path)
    destination.mkdir(parents=True, exist_ok=True)
    target = destination / 'r2e-campaign.tar.gz'
    with target.open('xb') as stream, tarfile.open(fileobj=stream, mode='w:gz', dereference=False) as archive:
        for path in members:
            archive.add(path, arcname=str(Path('campaign') / path.relative_to(campaign)), recursive=False)
    save_record(destination / 'recovery.json', {'files': len(members), 'input_bytes': total,
                'archive_bytes': target.stat().st_size, 'public_release': False})


def run(args):
    if os.environ.get('REPO2RLENV_MODEL_WORKER') != '1':
        raise RuntimeError('Approved remote model controller required')
    output = Path(os.environ['IRIS_OUTPUT_DIR'])
    profile = json.loads(args.profile.read_text())
    options = R2EOptions.model_validate(profile['options'])
    if options.target != 3 or options.max_candidates != 10 or options.max_rounds != 3:
        raise ValueError('Unexpected candidate/repair bounds')
    settings = json.loads(args.adaptation.read_text())
    if (settings['stage'] != 'generation_only' or settings['paid_fallback']
            or settings['max_output_tokens'] != 131072 or settings['reasoning_effort'] != 'medium'
            or settings['request_timeout_sec'] != 1200):
        raise ValueError('Unexpected generation settings')
    wheel_hash = check_runtime_wheel(args.wheel)
    args.campaign.mkdir(parents=True, exist_ok=False)
    # Native reservations are accounting units; GLM is the existing free endpoint.
    # At most 10 * (3 test-author calls + 1 specification call) are possible.
    ledger = BudgetLedger(args.campaign / 'budget.sqlite3', limit_usd='40')
    receipt = None
    state = {'stage': 'r2e_author_execute_refine_export', 'status': 'starting',
             'runtime_wheel_sha256': wheel_hash, 'max_model_requests': 40,
             'accepted_tasks': 0, 'blind_solver_attempts': 0}
    try:
        worker, receipt = provision_worker(WorkerSpec(provider='daytona', cpus=2,
            memory_mb=4096, disk_gb=10, timeout_sec=7200, name=args.worker_name),
            args.campaign / 'workers', ledger, reserve_usd='5')
        spec = GenerationInput.model_validate({
            'repo': profile['repo'], 'pipeline': {'name': 'equivalence_tests', 'recipe': 'r2e'},
            'llm': {'provider': 'openai', 'model': 'glm-5.3',
                    'endpoint': os.environ['BIOTASKS21_GLM_ENDPOINT'],
                    'api_key_env': 'BIOTASKS21_GLM_KEY', 'max_concurrent': 1,
                    'timeout_sec': 1200, 'fallback': None},
            'execution': {'worker_receipt': str(receipt.resolve()),
                          'runtime_wheel': str(args.wheel.resolve()),
                          'campaign_dir': str(args.campaign.resolve()),
                          'run_id': args.run_id, 'timeout_sec': 6600, 'resume': False},
            'output': {'destination': str((args.campaign / 'tasks').resolve()),
                       'org': 'open-athena', 'dataset_name': 'biotasks21-r2e'},
            'auth': {'use_gh_cli': False}})
        save_record(args.campaign / 'input-private.json', spec.model_dump(mode='json'))
        save_record(args.campaign / 'author-settings.json', {'profile': profile, 'adaptation': settings})
        pipeline = R2EPipeline(spec, options)
        def event(e):
            with (args.campaign / 'events.jsonl').open('a') as stream:
                stream.write(e.model_dump_json() + '\n')
        pipeline.set_event_callback(event)
        with adapted_authoring(settings, args.campaign, metering_target='r2e'):
            result = pipeline.run(args.campaign / 'tasks')
        state.update(status='completed', result=dataclasses.asdict(result))
        state['result']['out_dir'] = str(result.out_dir)
    except BaseException as exc:
        state.update(status='failed', error_type=type(exc).__name__)
        raise
    finally:
        signal.alarm(0)
        try:
            if receipt is not None:
                # Recover unfinished remote trials before terminating the worker.
                try:
                    script = """import pathlib,tarfile
roots=[pathlib.Path('/evidence'),pathlib.Path('/work/trials')]
files=[p for root in roots for p in root.rglob('*') if p.is_file() and not p.is_symlink()]
if sum(p.stat().st_size for p in files)>128*1024**2:raise ValueError('Capture bound')
with tarfile.open('/tmp/r2e-remaining.tar.gz','w:gz') as t:
 for p in files:t.add(p,arcname=str(p).lstrip('/'),recursive=False)
"""
                    worker.exec(['/opt/repo2rlenv/bin/python', '-c', script], timeout=120).checked('Capture remaining evidence')
                    worker.download('/tmp/r2e-remaining.tar.gz', args.campaign / 'remote-evidence.tar.gz')
                    state['remote_evidence_recovered'] = True
                except Exception as exc:
                    state['remote_evidence_error_type'] = type(exc).__name__
                stop_worker(receipt, ledger)
                from daytona.common.errors import DaytonaNotFoundError
                try:
                    worker.client.get(worker.id)
                    state['cleanup'] = 'still_present'
                except DaytonaNotFoundError:
                    state['cleanup'] = 'confirmed_absent_404'
        except BaseException as exc:
            state['cleanup_error_type'] = type(exc).__name__
        finally:
            save_record(args.campaign / 'controller-result.json', state)
            capture(args.campaign, output)


def main():
    parser = argparse.ArgumentParser()
    for name in ('campaign', 'wheel', 'profile', 'adaptation'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--worker-name', required=True)
    parser.add_argument('--run-id', required=True)
    args = parser.parse_args()
    for sig in (signal.SIGALRM, signal.SIGTERM, signal.SIGINT):
        signal.signal(sig, deadline)
    remaining = int(os.environ.get('BIOTASKS21_CONTROLLER_DEADLINE', '6900'))
    if not 60 <= remaining <= 6900:
        raise ValueError('Invalid controller deadline')
    signal.alarm(remaining)
    run(args)


if __name__ == '__main__':
    main()
