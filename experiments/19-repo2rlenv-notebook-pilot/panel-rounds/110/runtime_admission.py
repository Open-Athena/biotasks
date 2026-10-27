"""Admit reviewed general prompts and post-run provenance, preserving old proofs.

This source-only operator check grants neither funds nor provider access and
cannot establish scientific acceptance of the revised factory.
"""

import ast
import hashlib
import importlib.util
import json
import subprocess
import tarfile
import tempfile
from contextlib import contextmanager
from pathlib import Path, PurePosixPath

PREFIX = "experiments/19-repo2rlenv-notebook-pilot/"
PARENT = "c5061cbf937e801f5e41998fc0c06025770144fa"
PROMPT_REVISION = "c596055b"


def load(path):
    return json.loads(path.read_text())


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


@contextmanager
def frozen_parent(repo):
    selected, total = [], 0
    rows = subprocess.check_output(
        ["git", "ls-tree", "-r", "-l", PARENT], cwd=repo, text=True
    ).splitlines()
    for row in rows:
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
                        name.startswith(PREFIX + f"panel-rounds/{n:03}/") for n in range(100, 110)
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
    # Local source-proof working-set bound; never an LLM input limit.
    assert selected and total < 64 * 1024 * 1024
    with tempfile.TemporaryDirectory(prefix="biotasks19-parent109-proof-") as directory:
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


def prove_publication_only(before, after):
    def nodes(raw):
        return {
            getattr(node, "name", f"statement-{i}"): ast.dump(node, include_attributes=False)
            for i, node in enumerate(ast.parse(raw).body)
        }

    old, new = nodes(before), nodes(after)
    assert set(old) == set(new)
    changed = {name for name in old if old[name] != new[name]}
    assert changed == {"release_execution_provenance"}

    # Scientific/source/native completion predicate is identical in both paths.
    def completion(raw):
        return [
            ast.dump(node, include_attributes=False)
            for node in ast.walk(ast.parse(raw))
            if isinstance(node, ast.If) and "completed unattended pipeline" in ast.unparse(node)
        ]

    assert completion(before) == completion(after) and len(completion(after)) == 1


def candidate_admission(repo, runtime):
    repo = Path(repo).resolve()
    experiment = repo / PREFIX
    expected = load(experiment / "panel-rounds/110/candidate-runtime-identity.json")
    baseline = load(experiment / "panel-rounds/109/runtime-identity.json")["runtime_files"]
    assert runtime == expected["runtime_files"] and len(runtime) == 237
    assert all(digest((repo / name).read_bytes()) == sha for name, sha in runtime.items())
    deltas = {
        name: {"before": baseline.get(name), "after": sha}
        for name, sha in runtime.items()
        if baseline.get(name) != sha
    }
    assert not (baseline.keys() - runtime.keys()) and len(baseline) == 235
    assert deltas == expected["changed_or_added_files"] and len(deltas) == 7
    prompts = load(experiment / "panel-rounds/109/prompt-candidate.json")
    assert len(prompts["changes"]) == 3
    for name, row in prompts["changes"].items():
        assert runtime[name] == row["sha256"]
        assert (
            digest(subprocess.check_output(["git", "show", PROMPT_REVISION + ":" + name], cwd=repo))
            == row["sha256"]
        )
    checks = load(experiment / "panel-rounds/109/snapshot-publication-checks.json")
    assert checks["broader_distinct_tests_passed"] == 128
    for name, sha in checks["changed_sources"].items():
        assert runtime[PREFIX + name] == sha
    assert set(deltas) == set(prompts["changes"]) | {
        PREFIX + name for name in checks["changed_sources"]
    }
    old_publication = subprocess.check_output(
        ["git", "show", PARENT + ":" + PREFIX + "release_metadata.py"], cwd=repo
    )
    assert digest(old_publication) == baseline[PREFIX + "release_metadata.py"]
    prove_publication_only(old_publication, (experiment / "release_metadata.py").read_bytes())
    with frozen_parent(repo) as (view, proof):
        parent_experiment = view / PREFIX
        record = load(parent_experiment / "panel-rounds/109/source-admission.json")
        helper = parent_experiment / "panel-rounds/109/runtime_admission.py"
        assert digest(helper.read_bytes()) == record["admission_helper_sha256"]
        parent = module(helper, "frozen_parent109_admission").candidate_admission(view, baseline)
    assert not view.exists()
    allowed = dict(parent["allowed_source_deltas"])
    allowed.update({name: row["after"] for name, row in deltas.items()})
    return {
        **parent,
        "candidate": runtime,
        "reader_predecessor": baseline,
        "allowed_source_deltas": allowed,
        "parent_proofs_rechecked_from_frozen_source": proof,
        "parent_source_view_cleaned": True,
        "reviewed_prompt_revision": PROMPT_REVISION,
        "postrun_publication_tests": 128,
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
        )
    }, "Proof belongs to an unknown source family"
    assert admission["allowed_source_deltas"].get(name) == actual
    return "explicit_tested_candidate_delta_not_relabeling_original_live_proof"
