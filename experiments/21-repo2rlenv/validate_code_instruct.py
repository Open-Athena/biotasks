"""Execute saved candidates with native code-instruct validation, remotely.

An existing built image is required. This stage does not author, export, or
independently accept tasks. Native outcomes and complete command logs are saved.
"""

import argparse
import dataclasses
import json
import os
import re
import subprocess
from pathlib import Path

from repo2rlenv.bootstrap.docker import DockerSandbox
from repo2rlenv.execution.lifecycle import save_record
from repo2rlenv.pipelines.code_instruct import CodeInstructPipeline
from repo2rlenv.pipelines._oss_instruct import ParsedTask
from repo2rlenv.spec.options import CodeInstructOptions


class RecordingSandbox:
    def __init__(self, sandbox, output):
        self.sandbox = sandbox
        self.output = output
        self.calls = 0

    def exec(self, command, *, timeout):
        self.calls += 1
        result = self.sandbox.exec(command, timeout=timeout)
        save_record(self.output / f'command-{self.calls}.json', {
            'command': command, 'timeout_sec': timeout, **dataclasses.asdict(result),
        })
        return result


def validate_one(sandbox, record, output):
    filename = record['test_filename']
    if not re.fullmatch(r'test_r2e_[0-9a-f]{10}\.py', filename):
        raise ValueError('Unexpected native test filename')
    parsed = ParsedTask(**{key: record[key] for key in ('problem', 'test_code', 'solution_code')})
    pipeline = object.__new__(CodeInstructPipeline)
    pipeline.options = CodeInstructOptions()
    return pipeline._verify_task(RecordingSandbox(sandbox, output), parsed, test_filename=filename)


def main():
    if os.environ.get('REPO2RLENV_REMOTE_WORKER') != '1':
        raise RuntimeError('Approved remote CPU worker required')
    parser = argparse.ArgumentParser()
    parser.add_argument('--candidates', type=Path, required=True)
    parser.add_argument('--image', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    candidates = json.loads(args.candidates.read_text())
    if candidates['stage'] != 'authoring_only' or len(candidates['records']) > 10:
        raise ValueError('Unexpected candidate stage or count')
    args.output.mkdir(parents=True, exist_ok=False)
    image = subprocess.run(['docker', 'image', 'inspect', args.image, '--format', '{{.Id}}'],
                           capture_output=True, text=True, check=True, timeout=30).stdout.strip()
    results = []
    for index, candidate in enumerate(candidates['records']):
        record = {'candidate_index': index, 'stage': 'native_validation_running', 'image_id': image}
        results.append(record)
        save_record(args.output / 'summary.json', {'records': results})
        sandbox = None
        try:
            cid = subprocess.run(['docker', 'run', '-d', '--network', 'none', '--cpus', '1',
                '--memory', '2048m', '-w', '/workspace', image, 'sleep', 'infinity'],
                capture_output=True, text=True, check=True, timeout=60).stdout.strip()
            if not cid:
                raise RuntimeError('No container identity returned')
            sandbox = DockerSandbox(cid, '', 'linux/amd64')
            outcome = validate_one(sandbox, candidate, args.output / str(index))
            record.update(stage='native_validation_completed', **dataclasses.asdict(outcome))
        except Exception as exc:
            record.update(stage='native_validation_error', error_type=type(exc).__name__)
        finally:
            if sandbox is not None:
                sandbox.cleanup()
                record['cleanup_requested'] = True
            save_record(args.output / 'summary.json', {'records': results})


if __name__ == '__main__':
    main()
