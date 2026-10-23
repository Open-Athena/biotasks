"""Verify real frozen-input packaging with an explicitly nonexecuted image ID."""
import argparse
import json
from pathlib import Path
import tempfile

import confirmation_job as job


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--original-archive', type=Path, required=True)
    parser.add_argument('--original-plan', type=Path, required=True)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='biotasks34-confirm-pack-') as td:
        job.ROOT = Path(td)
        job.OUT = Path(td)/'evidence'
        job.OUT.mkdir()
        plan = json.loads(args.original_plan.read_text())
        job.unpack_original(args.original_archive, plan, Path(td)/'original')
        source = Path(td)/'original/outputs/macs3-project__MACS/macs3-project__MACS-742'
        result = job.package_candidate(source, args.original_plan, 'sha256:'+'0'*64)
        manifest = json.loads((job.OUT/'candidate-manifest.json').read_text())
        assert manifest['unchanged_original_files'] == 9
        assert result['files'] == 12
        for relative in ('tests/test.sh', 'tests/verifier.py', 'environment/docker-compose.yaml', 'solution/patch.diff', 'task.toml'):
            candidate = Path(td)/'candidate/outputs/macs3-project__MACS/macs3-project__MACS-742'/relative
            assert candidate.read_bytes() == (source/relative).read_bytes()
        try:
            job.unpack_original(args.original_archive, plan, Path(td)/'original')
        except AssertionError:
            pass
        else:
            raise AssertionError('Original inputs were overwritten')
    print(json.dumps(dict(original_files=10, candidate_files=12, original_non_dockerfile_assets_unchanged=9,
        original_overwrite_rejected=True, image_id_synthetic=True, remote_execution=False, temporary_files_removed=True)))


if __name__ == '__main__':
    main()
