"""Recheck frozen parent proofs and explicitly admit shared reader/export code.

Operator-only source admission. It does not grant funding, provider access,
scientific acceptance or additional model/time/resource/repair allowances.
"""

import hashlib
import importlib.util
import json
import subprocess
import tarfile
import tempfile
from contextlib import contextmanager
from pathlib import Path, PurePosixPath

PREFIX = "experiments/19-repo2rlenv-notebook-pilot/"
PARENT = "2a8392bee42d7ac110c5aecc52f01eb755a4f0c5"


def load(path):
    return json.loads(path.read_text())


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


@contextmanager
def frozen_parent(repo):
    """A small source-only clone shares objects and never edits the main checkout."""
    records = subprocess.check_output(
        ["git", "ls-tree", "-r", "-l", PARENT], cwd=repo, text=True
    ).splitlines()
    selected, total = [], 0
    for row in records:
        metadata, name = row.split("\t", 1)
        _, kind, _, size = metadata.split()
        path = PurePosixPath(name)
        wanted = (
            name in {"pyproject.toml", "uv.lock", ".python-version", "README.md", "LICENSE"}
            or name.startswith("src/")
            or (
                name.startswith(PREFIX)
                and (
                    path.parent == PurePosixPath(PREFIX.rstrip("/"))
                    or name.startswith(PREFIX + "patches/")
                    or name.startswith(PREFIX + "factory-checks/")
                    or any(
                        name.startswith(PREFIX + "panel-rounds/" + number + "/")
                        for number in ("100", "101", "102", "103", "104", "105", "107", "108")
                    )
                )
            )
        )
        if (
            kind == "blob"
            and wanted
            and (
                path.suffix in {".py", ".json", ".md", ".toml", ".lock", ".txt", ".patch", ".sh"}
                or name in {".python-version", "LICENSE"}
            )
        ):
            selected.append(name)
            total += int(size)
    # Local operator working-set bound, never a worker/model/data-input limit.
    assert selected and total < 64 * 1024 * 1024
    with tempfile.TemporaryDirectory(prefix="biotasks19-parent108-proof-") as directory:
        view = Path(directory) / "source"
        subprocess.run(
            [
                "git",
                "-c",
                "gc.auto=0",
                "clone",
                "--quiet",
                "--shared",
                "--no-checkout",
                str(repo),
                str(view),
            ],
            check=True,
        )
        with tempfile.TemporaryFile() as archive:
            subprocess.run(
                [
                    "git",
                    "archive",
                    "--format=tar",
                    PARENT,
                    "--",
                    *[":(literal)" + p for p in selected],
                ],
                cwd=repo,
                stdout=archive,
                check=True,
            )
            archive.seek(0)
            with tarfile.open(fileobj=archive, mode="r|") as source:
                for member in source:
                    if member.isdir():
                        continue
                    assert member.isfile() and member.name in selected
                    target = view / member.name
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(source.extractfile(member).read())
        yield (
            view,
            {
                "revision": PARENT,
                "source_files": len(selected),
                "source_bytes": total,
                "local_shared_objects_only": True,
            },
        )


def candidate_admission(repo, runtime):
    repo = Path(repo).resolve()
    experiment = repo / PREFIX
    expected = load(experiment / "factory-checks/table-parsing/candidate-runtime-identity.json")
    assert runtime == expected["runtime_files"] and len(runtime) == 235
    assert all(digest((repo / name).read_bytes()) == sha for name, sha in runtime.items())
    baseline = load(experiment / "panel-rounds/108/runtime-identity-224.json")["runtime_files"]
    assert len(baseline) == 232 and not (baseline.keys() - runtime.keys())
    assert {
        name: {"before": baseline.get(name), "after": sha}
        for name, sha in runtime.items()
        if baseline.get(name) != sha
    } == expected["changed_or_added_files"]
    assert len(expected["changed_or_added_files"]) == 14

    # Execute the original validator on its original bytes, rather than relaxing
    # old proof predicates to make them accept unrelated current source files.
    with frozen_parent(repo) as (view, parent_source):
        parent_experiment = view / PREFIX
        record = load(parent_experiment / "panel-rounds/108/source-admission.json")
        helper = parent_experiment / "panel-rounds/108/runtime_admission.py"
        assert digest(helper.read_bytes()) == record["admission_helper_sha256"]
        assert all(digest((view / name).read_bytes()) == sha for name, sha in baseline.items())
        parent = module(helper, "frozen_parent108_admission").candidate_admission(view, baseline)
    assert not view.exists()

    snapshot_root = experiment / "factory-checks/primary-snapshot"
    snapshot = module(snapshot_root / "prove_boundary.py", "snapshot109_boundary")
    for name, check in (
        ("iris_bootstrap.py", snapshot.prove_bootstrap),
        ("run_autonomous.py", snapshot.prove_controller),
    ):
        check(snapshot.original(name), (experiment / name).read_bytes())
    transport_checks = load(snapshot_root / "offline-checks.json")
    assert transport_checks["tests_passed"] == 158
    for name, row in transport_checks["runtime_changes"].items():
        assert runtime[name] == row["after"]
    reader_root = experiment / "factory-checks/table-parsing"
    reader = module(reader_root / "prove_boundary.py", "reader109_boundary")
    for name, check in reader.CHECKS.items():
        check(reader.original(name), (repo / name).read_bytes())
    checks = load(reader_root / "offline-checks.json")
    assert checks["final_combined_tests_passed"] == 498
    assert checks["license_full_copy_identity_verified"]
    assert checks["source_boundary_and_refusal_tests"] == 10
    proof = load(reader_root / checks["source_boundary"])
    for name, row in proof["controller_changes"].items():
        assert runtime[name] == row["after"]
    allowed = dict(parent["allowed_source_deltas"])
    allowed.update({name: sha for name, sha in runtime.items() if baseline.get(name) != sha})
    return {
        **parent,
        "common_predecessor": baseline,
        "candidate": runtime,
        "allowed_source_deltas": allowed,
        "parent_proofs_rechecked_from_frozen_source": parent_source,
        "parent_source_view_cleaned": True,
        "new_shared_reader_live_verified": False,
        "new_primary_snapshot_live_verified": False,
        "new_whole_pipeline_live_qualified": False,
        "new_source_funding_typed_pool_and_cleanup_checks_still_required": True,
    }


def check_source(admission, name, expected):
    actual = admission["candidate"][name]
    if actual == expected:
        return "exact_previous_proof_bytes"
    assert isinstance(expected, str) and expected in {
        admission[key].get(name)
        for key in (
            "old",
            "predecessor",
            "lifecycle_predecessor",
            "creation_predecessor",
            "feedback_predecessor",
            "common_predecessor",
        )
    }, "Proof belongs to an unknown source family"
    assert admission["allowed_source_deltas"].get(name) == actual
    return "explicit_tested_candidate_delta_not_relabeling_original_live_proof"
