"""Synthetic Docker-transport checks; does not claim a live image capture."""
from copy import deepcopy
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

from capture_build_receipt import capture


class FakeDocker:
    def __init__(self):
        self.calls = []
        self.owner = 'test-owner'
        self.fail_copy = False
        self.receipt = dict(plan=dict(base_commit='a'*40, pyproject_sha256='b'*64,
            target_distribution='macs3', build_requirements=['setuptools']),
            python='synthetic', platform='synthetic', wheels=[dict(name='setuptools',
            filename='setuptools-1-py3-none-any.whl', sha256='c'*64, bytes=100)])

    def __call__(self, command, **kwargs):
        self.calls.append(command[1:])
        if command[1:3] == ['image', 'inspect']:
            info = dict(Id='sha256:'+'d'*64, Config=dict(Labels={'biotasks.run': self.owner}, Env=['PIP_NO_INDEX=1']))
            return subprocess.CompletedProcess(command, 0, json.dumps([info]), '')
        if command[1] == 'cp':
            if self.fail_copy:
                raise subprocess.CalledProcessError(1, command)
            Path(command[-1]).write_text(json.dumps(self.receipt))
        return subprocess.CompletedProcess(command, 0, '', '')


class CaptureChecks(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='biotasks34-capture-check-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.docker = FakeDocker()

    def capture(self):
        return capture('docker', 'test-owner', 'test-image', self.root, run=self.docker)

    def test_stopped_capture_and_unchanged_repeat(self):
        first = self.capture()
        self.assertEqual(first, self.capture())
        self.assertTrue((self.root / first['file']).exists())
        self.assertTrue(first['captured_before_task_start'])
        self.assertFalse(any(c[0] in ('start', 'run', 'exec') for c in self.docker.calls))
        create = next(c for c in self.docker.calls if c[0] == 'create')
        for flag in ('--network=none', '--cpus=1', '--memory=128m', '--memory-swap=128m'):
            self.assertIn(flag, create)
        self.assertEqual(self.docker.calls[-1][0], 'rm')

    def test_foreign_image_never_creates_container(self):
        self.docker.owner = 'someone-else'
        with self.assertRaises(AssertionError): self.capture()
        self.assertEqual(len(self.docker.calls), 1)

    def test_missing_receipt_still_removes_owned_container(self):
        self.docker.fail_copy = True
        with self.assertRaises(subprocess.CalledProcessError): self.capture()
        self.assertEqual(self.docker.calls[-1][0], 'rm')
        self.assertEqual(list(self.root.rglob('*.partial')), [])

    def test_target_wheel_refused(self):
        self.docker.receipt['wheels'][0]['name'] = 'MACS3'
        with self.assertRaises(AssertionError): self.capture()
        self.assertEqual(self.docker.calls[-1][0], 'rm')
        self.assertEqual(list(self.root.rglob('*.json')), [])

    def test_changed_receipt_preserves_original(self):
        first = self.capture()
        before = (self.root / first['file']).read_bytes()
        self.docker.receipt = deepcopy(self.docker.receipt)
        self.docker.receipt['wheels'][0]['sha256'] = 'e'*64
        with self.assertRaises(AssertionError): self.capture()
        self.assertEqual((self.root / first['file']).read_bytes(), before)
        self.assertEqual(list(self.root.rglob('*.partial')), [])


if __name__ == '__main__':
    unittest.main()
