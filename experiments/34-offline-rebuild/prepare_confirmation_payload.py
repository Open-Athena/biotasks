"""Freeze all no-model combined-run inputs; never launch remote work."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import tempfile

from confirmation_job import unpack_original

ROOT = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--original-archive', type=Path, required=True)
    parser.add_argument('--original-plan', type=Path, required=True)
    args = parser.parse_args()
    destination = ROOT/'inputs-private/confirmation-payload'
    assert not destination.exists(), 'Never overwrite a prepared payload'
    files = {name: ROOT/name for name in [
        'confirmation_job.py', 'confirmation_replay.py', 'replay_macs_742_image.py',
        'recorded_replay.py', 'post_check_limits.py', 'docker-tool.json',
        'confirmation_control_supervisor.py', 'cleanup_owned.py', 'harbor_docker_receipts.py',
        'capture_build_receipt.py', 'setup_controller.sh', 'run_existing_controls.py',
        'prepare_control_variant.py', 'macs-base-dependency-plan.json',
        'offline_dependencies.py', 'prepare_build_cache.py',
    ]}
    files.update({
        'replay.json': ROOT/'inputs-private/macs-recorded-replay.json',
        'docker_original.py': ROOT/'upstream/bootstrap/docker.py',
        'runner_original.py': ROOT/'upstream/bootstrap/runner.py',
        'auth_original.py': ROOT/'upstream/auth.py',
        'pins.json': ROOT/'control-pins.json',
        'original-export.tar.gz': args.original_archive,
        'original-control-plan.json': args.original_plan,
    })
    with tempfile.TemporaryDirectory(prefix='biotasks34-input-check-') as td:
        unpack_original(args.original_archive, json.loads(args.original_plan.read_text()), Path(td))
    assert sum(p.stat().st_size for p in files.values()) < 1024**2
    destination.mkdir(mode=0o700, parents=True)
    for name, source in files.items():
        assert not source.is_symlink()
        shutil.copyfile(source, destination/name)
    hashes = {name: hashlib.sha256((destination/name).read_bytes()).hexdigest() for name in files}
    source_pins = {name: hashes[name] for name in ('docker_original.py', 'runner_original.py', 'auth_original.py')}
    (destination/'source-pins.json').write_text(json.dumps(source_pins)+'\n')
    hashes['source-pins.json'] = hashlib.sha256((destination/'source-pins.json').read_bytes()).hexdigest()
    manifest = dict(run_id='biotasks34-macs-742-confirm-001', sha256=hashes,
        original_files_verified=10, model_calls=0, maximum_cpu_hours=8,
        adaptations=['Run ownership and evidence subdirectories',
                     'Same trusted base-declared offline dependency cache',
                     'Receipt capture before task startup',
                     'Automatic sequential reconstruction, packaging and controls'])
    (destination/'confirmation-payload.json').write_text(json.dumps(manifest, indent=2)+'\n')
    (ROOT/'confirmation-payload-manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
    print(json.dumps(dict(payload_files=len(hashes)+1, original_files_verified=10, submitted=False)))


if __name__ == '__main__':
    main()
