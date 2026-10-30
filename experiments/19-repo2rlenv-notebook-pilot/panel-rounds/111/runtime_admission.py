"""Admit one explicit post-native-review source version, never a live outcome."""

import hashlib
import importlib.util
import json
import subprocess
import tarfile
import tempfile
from contextlib import contextmanager
from pathlib import Path, PurePosixPath

PREFIX = "experiments/19-repo2rlenv-notebook-pilot/"
PARENT = "7b51adb0d60783018f2e999154c21e575cb8819e"
DELTAS = {
    PREFIX + name
    for name in (
        "admission_profile.py",
        "native_review.py",
        "test_native_review.py",
        "test_native_review_release.py",
        "run_autonomous.py",
        "test_autonomous.py",
        "release_metadata.py",
        "check_scientific_release.py",
        "scientific_bundle.py",
        "test_scientific_bundle.py",
    )
} | {
    "src/biotasks/prompts/notebook-native-review.md",
    "src/biotasks/prompts/notebook-task-specification.md",
}


def load(path):
    return json.loads(path.read_text())


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def module(path):
    spec = importlib.util.spec_from_file_location("frozen_source110_admission", path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


@contextmanager
def frozen_parent(repo):
    """Replay the original 110 validator on its own unmodified source tree."""
    selected, total = [], 0
    for row in subprocess.check_output(
        ["git", "ls-tree", "-r", "-l", PARENT], cwd=repo, text=True
    ).splitlines():
        metadata, name = row.split("\t", 1)
        mode, kind, _, size = metadata.split()
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
                        name.startswith(PREFIX + f"panel-rounds/{n:03}/") for n in range(100, 111)
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
            assert mode in {"100644", "100755"}
            selected.append(name)
            total += int(size)
    # Local source-proof footprint only; not a model or biological input cap.
    assert selected and total < 64 * 1024 * 1024
    with tempfile.TemporaryDirectory(prefix="biotasks19-source110-proof-") as directory:
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
            dict(revision=PARENT, files=len(selected), bytes=total, local_shared_objects_only=True),
        )


def candidate_admission(repo, runtime):
    repo = Path(repo).resolve()
    experiment = repo / PREFIX
    expected = load(experiment / "panel-rounds/111/candidate-runtime-identity.json")
    baseline = load(experiment / "panel-rounds/110/candidate-runtime-identity.json")[
        "runtime_files"
    ]
    assert runtime == expected["runtime_files"]
    assert not (baseline.keys() - runtime.keys())
    assert all(digest((repo / name).read_bytes()) == sha for name, sha in runtime.items())
    deltas = {
        name: {"before": baseline.get(name), "after": sha}
        for name, sha in runtime.items()
        if baseline.get(name) != sha
    }
    assert set(deltas) == DELTAS and deltas == expected["changed_or_added_files"]
    checks = load(experiment / "factory-checks/native-review/release-integration-checks.json")
    assert checks["tests"]["passed"] == 175 and checks["tests"]["exit_status"] == 0
    assert checks["new_model_requests"] == checks["new_jobs_or_sandboxes"] == 0
    for name, sha in checks["source_files"].items():
        assert runtime[name] == sha
    initial = load(experiment / "factory-checks/native-review/checks.json")
    assert initial["final_tests"]["passed"] == 100
    # Only the initial prompt files are still the same byte version. The new
    # integration receipt, not an old pass count, binds the revised programs.
    for name in (
        "src/biotasks/prompts/notebook-native-review.md",
        "src/biotasks/prompts/notebook-task-specification.md",
    ):
        assert runtime[name] == initial["source_files"][name]
    with frozen_parent(repo) as (view, proof):
        prior = view / PREFIX / "panel-rounds/110"
        record = load(prior / "source-admission.json")
        helper = prior / "runtime_admission.py"
        assert digest(helper.read_bytes()) == record["admission_helper_sha256"]
        parent = module(helper).candidate_admission(view, baseline)
    assert not view.exists()
    allowed = dict(parent["allowed_source_deltas"])
    allowed.update({name: row["after"] for name, row in deltas.items()})
    return {
        **parent,
        "candidate": runtime,
        "rollout_review_predecessor": baseline,
        "allowed_source_deltas": allowed,
        "parent_proofs_rechecked_from_frozen_source": proof,
        "parent_source_view_cleaned": True,
        "offline_review_and_release_checks": 175,
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
            "reader_predecessor",
            "rollout_review_predecessor",
        )
    }, "Proof belongs to an unknown source family"
    assert admission["allowed_source_deltas"].get(name) == actual
    return "explicit_tested_candidate_delta_not_relabeling_original_live_proof"
