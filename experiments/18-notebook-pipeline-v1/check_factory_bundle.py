"""Exercise actual packaged worker imports and seed identities without services."""

import hashlib
import io
import json
import subprocess
import sys
import tempfile
import types
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from iris_factory_backend import IrisFactoryBackend

from biotasks.factory_stage import worker_template

REPO = Path(__file__).resolve().parents[2]


class Record:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


class Client:
    def __init__(self):
        self.calls = []

    def submit(self, **kwargs):
        self.calls.append(kwargs)
        return Record(job_id="/test/job")


def fake_iris():
    values = {
        "iris.cluster.constraints": {
            "Constraint": Record(create=lambda **kwargs: kwargs), "ConstraintOp": Record(EQ="eq")
        },
        "iris.cluster.setup_scripts": {"default_setup_script": lambda **kwargs: kwargs},
        "iris.cluster.types": {key: Record for key in ("Entrypoint", "EnvironmentSpec", "ResourceSpec")},
        "iris.rpc": {"job_pb2": Record(PRIORITY_BAND_BATCH=1)},
        "rigging.timing": {"Duration": Record(from_seconds=lambda seconds: seconds)},
    }
    modules = {}
    for name, attrs in values.items():
        module = types.ModuleType(name)
        module.__dict__.update(attrs)
        modules[name] = module
    return modules


class BundleChecks(unittest.TestCase):
    def test_unique_seed_submission_and_importable_flat_bundle(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            dummy = root / "dummy"
            dummy.write_bytes(b"fixture")
            digest = hashlib.sha256(dummy.read_bytes()).hexdigest()
            client = Client()
            backend = IrisFactoryBackend(
                client, REPO, dummy, digest, dummy, digest, "test-token", "/test/endpoint",
                "s3://test/factory", "test-cluster", "test-key",
            )
            template = worker_template("specification", 12, 300)
            template["input_zip_sha256"] = digest
            batch = {
                "factory_revision": "a" * 40, "execution_mode": "seed_pipeline",
                "workflow_version": 2, "entries": {"unseen": template},
                "stage_templates": {"specification": template},
                "seed_execution": {"seed_timeout_seconds": 7200},
            }
            with (
                patch.dict(sys.modules, fake_iris()),
                patch("iris_factory_backend.checkpoint_file", side_effect=lambda repo, rev, path: (repo / path).read_bytes()),
                patch("iris_factory_backend.subprocess.run", return_value=Record(stdout="\n".join(
                    str(path.relative_to(REPO)) for path in (REPO / "src/biotasks").rglob("*")
                    if path.suffix in {".py", ".md"}
                ))),
            ):
                for batch_id in ("b" * 64, "c" * 64):
                    backend(batch_id + ":unseen:seed_pipeline", batch, dummy)
            self.assertEqual(len({call["name"] for call in client.calls}), 2)
            first = client.calls[0]
            expected = "biotasks-factory-" + hashlib.sha256(("b" * 64 + ":unseen:seed_pipeline").encode()).hexdigest()[:32]
            self.assertEqual(first["name"], expected)
            self.assertTrue(first["environment"].env_vars["BIOTASKS_ARTIFACT_PREFIX"].endswith("/" + expected))
            self.assertEqual(first["max_retries_failure"], 0)
            self.assertEqual(first["max_retries_preemption"], 0)
            files = first["entrypoint"].workdir_files
            self.assertTrue(all("/" not in name for name in files))
            for name, data in files.items():
                (root / name).write_bytes(data)
            with zipfile.ZipFile(io.BytesIO(files["harbor-input.zip"])) as native:
                with zipfile.ZipFile(io.BytesIO(files["factory-runtime.zip"])) as runtime:
                    for name in runtime.namelist():
                        self.assertEqual(native.read(name), runtime.read(name))
            self.assertEqual(json.loads(files["pipeline.json"])["input_zip_sha256"], digest)
            # Stub only service imports, using the actual executor and all factory
            # modules in a fresh interpreter with editable installs disabled.
            (root / "fsspec.py").write_text("")
            (root / "iris/client").mkdir(parents=True)
            (root / "iris/cluster").mkdir()
            (root / "iris/client/client.py").write_text("iris_ctx = None\n")
            (root / "iris/cluster/types.py").write_text("JobName = None\n")
            # A stale package beside the entrypoint must not win import lookup.
            (root / "biotasks").mkdir()
            (root / "biotasks/__init__.py").write_text("raise RuntimeError('ambient package used')\n")
            result = subprocess.run(
                [sys.executable, "-S", *first["entrypoint"].command[1:], "--check-imports"],
                cwd=root, capture_output=True, text=True, timeout=10,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("no pipeline stages executed", result.stdout)


if __name__ == "__main__":
    unittest.main()
