"""Restore exact admitted inputs from existing public snapshots on free TRC."""

import hashlib
import importlib.metadata
import json
import os
import shutil
import subprocess
import sys
import tarfile
import time
from pathlib import Path

from prepare_authored_solver_inputs import restore


def main():
    os.environ['BIOTASKS21_BATCH_STARTED_MONOTONIC'] = str(time.monotonic())
    output = Path(os.environ['IRIS_OUTPUT_DIR'])
    output.mkdir(parents=True, exist_ok=True)
    state = {'stage': 'restore_exact_admitted_authored_inputs', 'status': 'started',
             'model_calls': 0, 'provider_allocations': 0, 'units': []}
    try:
        from huggingface_hub import HfApi

        if Path('run_glm_transport_probe.py').is_file():
            preflight_env = {k: v for k, v in os.environ.items() if k != 'DAYTONA_API_KEY'}
            subprocess.run([sys.executable, 'run_glm_transport_probe.py'],
                           env=preflight_env, check=True, timeout=240)
            preflight = json.loads((output / 'transport-probe.json').read_text())
            assert preflight['passed'] and preflight['model_calls'] == 0
            state['zero_model_transport_preflight_passed'] = True

        assert importlib.metadata.version('huggingface-hub') == '1.33.0'
        raw = Path('authored-source-inputs.json').read_bytes()
        assert hashlib.sha256(raw).hexdigest() == os.environ['BIOTASKS21_SOURCE_INPUTS_SHA256']
        inputs = json.loads(raw)
        api = HfApi(token=False)
        cohort = Path('cohort')
        cohort.mkdir(exist_ok=False)
        units = []
        for item in inputs['units']:
            assert item['unit'] in {'enspie', 'lcc', 'tsallis', 'pielou'}
            assert item['bucket'] == 'open-athena/biotasks'
            assert item['archive_path'].startswith('research/21-repo2rlenv/')
            archive = Path(item['unit'] + '-native.tar.gz')
            api.download_bucket_files(item['bucket'], [(item['archive_path'], archive)],
                                      raise_on_missing_files=True, token=False)
            assert archive.stat().st_size == item['archive_bytes']
            with archive.open('rb') as stream:
                assert hashlib.file_digest(stream, 'sha256').hexdigest() == item['archive_sha256']
            root = Path(item['unit'] + '-canonical')
            root.mkdir(exist_ok=False)
            total = 0
            with tarfile.open(archive, 'r|gz') as tar:
                for member in tar:
                    relative = Path(member.name)
                    assert not relative.is_absolute() and '..' not in relative.parts
                    if member.isdir():
                        continue
                    selected = (member.name.startswith('native/authored/native-task/') or
                                member.name.startswith('native/authored/profile-delta/') or
                                member.name in {'native/authored/control-manifest.json',
                                                'native/authored/canonical-task-storage.json'})
                    if not selected:
                        continue
                    assert member.isfile() and member.size < 64 * 1024**2
                    total += member.size
                    assert total < 512 * 1024**2
                    target = root / relative
                    target.parent.mkdir(parents=True, exist_ok=True)
                    with tar.extractfile(member) as source, target.open('xb') as destination:
                        shutil.copyfileobj(source, destination, 65536)
                    target.chmod(member.mode & 0o777)
            record = restore(root / 'native/authored', item['admission'], cohort / item['unit'])
            shutil.copyfile('native-sdk-preflight.json', cohort / item['unit'] / 'native-sdk-preflight.json')
            units.append(record)
            state['units'].append({**record, 'archive_sha256_verified': item['archive_sha256'],
                                   'restored_bytes': total})
        assert 1 <= len(units) <= 3
        assert len({item['unit'] for item in units}) == len(units)
        assert {item['unit'] for item in units} == {item['unit'] for item in inputs['units']}
        manifest = {'units': units, 'sequential': True, 'maximum_simultaneous_sandboxes': 2,
                    'one_blind_attempt_after_provider_controls': True,
                    'minimum_inference_lifetime_before_unit_seconds': 930}
        (cohort / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
        state.update(status='restored_all_admitted_hashes_and_modes_verified',
                     native_task_assets_changed=False)
        (output / 'canonical-restore-result.json').write_text(json.dumps(state, indent=2) + '\n')
        os.environ['BIOTASKS21_CANONICAL_RESTORE'] = 'verified'
        from run_continuation_trial_batch_trc import main as run_batch
        return run_batch()
    except Exception as exc:
        state.update(status='restore_or_controller_failure', error_type=type(exc).__name__)
        return 1
    finally:
        (output / 'canonical-restore-result.json').write_text(json.dumps(state, indent=2) + '\n')
        print(json.dumps(state), flush=True)


if __name__ == '__main__':
    raise SystemExit(main())
