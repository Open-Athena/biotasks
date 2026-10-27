"""Recognize one source-bound pre-dispatch failure; never synthesize a trial receipt."""

import hashlib
import json
import tarfile
import tomllib
import zipfile
from pathlib import Path

PREFIX = "experiments/19-repo2rlenv-notebook-pilot/"
SOURCES = {
    PREFIX
    + "iris_bootstrap.py": "a17acb66767f33044f81f7bd6ed8c4872178b8d154d36f623f87d459420b7d99",
    PREFIX
    + "iris_execution.py": "086c481d0925af19c7eef6d0a0a67df8a5dd8c1c1d7888551bf4c53504613ac9",
    PREFIX
    + "run_scientific_native.py": "0c7feba309d2a40d5f011edf1a4d3ed116bfec988d0d54932515a2a45afc038b",
}
UPSTREAM = "bb1bdd1aa3246ba773575eb596b40b5b7eb7baca6f7e7a851c20015d6313e05b"
RAW_UPSTREAM = "fdca449f7c304db3245b10d4c0c3af5e2e84932a48c54c8e10e917253f6839e8"
PIN = "b52061bc39fe11d7cd52abe0d7aef89ad01561412088f68712feded0bbf7e2ab"
MESSAGE = "An agent limit requires a blind trial and a finite task timeout"


def verify_refusal(
    *, pipeline, result, execution, task, claims, paths, log, source_hashes, upstream_sha256
):
    """Apply only to the recorded creator/native/upstream source family.

    In those exact sources, the quoted upstream argument guard precedes all
    worker commands, uploads, supervisor creation and sandbox creation. Both
    deterministic trials must have completed. Missing files alone never prove
    non-dispatch: the complete original traceback and exact source identities
    are required as well.
    """
    assert {name: source_hashes[name] for name in SOURCES} == SOURCES
    assert upstream_sha256 == UPSTREAM
    assert pipeline["status"] == "infrastructure_failed"
    assert pipeline["failed_stage"] == "native" and pipeline["error_type"] == "ValueError"
    assert pipeline["operator_interventions"] == 0
    assert result["status"] == "incomplete" and result["solver"] is None
    assert result["publication_ready"] is False
    assert [
        (r["agent"], r["reward"], r["passed"], r["cleanup_verified"], r["exception_type"])
        for r in result["controls"]
    ] == [
        ("oracle", 1, True, True, None),
        ("nop", 0, True, True, None),
    ]
    assert execution["adapter_sha256"] == SOURCES[PREFIX + "iris_execution.py"]
    assert execution["solver_seconds"] == task["agent"]["timeout_sec"] == 600
    assert execution["max_solver_attempts"] == 1 and execution["max_trials"] == 3
    assert log.rstrip().endswith("ValueError: " + MESSAGE)
    assert (
        'huggingface-Repo2RLEnv-5555443/src/repo2rlenv/execution/harbor.py", line 257, in run_trial'
        in log
    )
    assert 'iris_execution.py", line 206, in run_trial' in log
    assert 'run_scientific_native.py", line 105, in run' in log
    assert set(claims) == {"oracle", "nop", "terminus-2"}
    prefix = claims["oracle"]["trial_id"].removesuffix("-oracle")
    assert prefix.endswith("-native")
    for agent, claim in claims.items():
        assert claim["trial_id"] == prefix + "-" + agent
        assert claim["solving"] is (agent == "terminus-2")
        if agent != "terminus-2":
            assert claim["cleanup_verified"] is True
    assert set(p for p in paths if p.startswith("native/") and p.endswith("/remote-job.json")) == {
        "native/oracle/remote-job.json",
        "native/nop/remote-job.json",
    }
    assert not any(p.startswith("native/terminus-2/") for p in paths)
    return {
        "trial_id": claims["terminus-2"]["trial_id"],
        "dispatch_disproven_by_original_trace_and_exact_source": True,
        "original_outcome_receipt_present": False,
        "original_claim_unchanged": True,
        "scientific_acceptance_or_solver_result_inferred": False,
        "method": "Exact source-bound upstream argument refusal before every remote operation; complete original archive contains only the two completed deterministic jobs.",
    }


def verify_original_refusal(archive, submission, payload):
    """Bind the pure check to complete original exports and submitted archives."""
    archive, payload = Path(archive), Path(payload)

    def digest(raw):
        return hashlib.sha256(raw).hexdigest()

    def files(root, manifest_name, readback_name, verified_key, hash_key):
        raw = (root / manifest_name).read_bytes()
        readback = json.loads((root / readback_name).read_text())
        assert readback[verified_key] and readback[hash_key] == digest(raw)
        entries = {row["path"]: row for row in json.loads(raw)["files"]}

        def original(name):
            path = root / "files" / name
            assert not path.is_symlink()
            assert path.stat().st_mode & 0o777 == entries[name]["mode"]
            data = path.read_bytes()
            assert len(data) == entries[name]["bytes"] and digest(data) == entries[name]["sha256"]
            return data

        return entries, original

    entries, original = files(
        archive,
        "sealed-manifest.json",
        "independent-readback.json",
        "all_files_download_verified",
        "source_manifest_sha256",
    )
    _, root_original = files(
        archive / "root-evidence",
        "sealed-root-manifest.json",
        "readback.json",
        "all_manifest_files_hash_size_mode_verified",
        "root_manifest_sha256",
    )

    def submitted_members(name, select):
        path = payload / name
        assert digest(path.read_bytes()) == submission["inputs"]["files"][name]
        result = {}
        with tarfile.open(path) as source:
            for member in source:
                key = select(member.name)
                if key is None:
                    continue
                assert key not in result and member.isfile()
                result[key] = source.extractfile(member).read()
        return result

    selected = submitted_members(
        "biotasks.tar",
        lambda name: next(
            (
                key
                for key in {*SOURCES, PREFIX + "upstream-pin.json"}
                if name == key or name.endswith("/" + key)
            ),
            None,
        ),
    )
    assert set(selected) == {*SOURCES, PREFIX + "upstream-pin.json"}
    pin_raw = selected.pop(PREFIX + "upstream-pin.json")
    assert digest(pin_raw) == PIN
    pin = json.loads(pin_raw)
    patch_names = {PREFIX + row["path"]: row["sha256"] for row in pin["patches"]}
    patches = submitted_members(
        "biotasks.tar",
        lambda name: next(
            (key for key in patch_names if name == key or name.endswith("/" + key)), None
        ),
    )
    assert {name: digest(raw) for name, raw in patches.items()} == patch_names
    upstream_path = "src/repo2rlenv/execution/harbor.py"
    upstream = submitted_members(
        "upstream.tar.gz",
        lambda name: (
            upstream_path if name == upstream_path or name.endswith("/" + upstream_path) else None
        ),
    )
    assert set(upstream) == {upstream_path}
    raw_upstream_hash = digest(upstream[upstream_path])
    assert raw_upstream_hash == RAW_UPSTREAM
    # The frozen bootstrap applies the pinned patch chain before building the
    # archived wheel. A long-lived operator client's patched checkout is not
    # evidence of the bytes that executed in this campaign.
    wheel = root_original("runtime/repo2rlenv-0.9.3-py3-none-any.whl")
    import io

    with zipfile.ZipFile(io.BytesIO(wheel)) as package:
        upstream_hash = digest(package.read("repo2rlenv/execution/harbor.py"))
        assert upstream_hash == UPSTREAM
    claims = {}
    for name in entries:
        if name.startswith("native/trial-claims/") and name.endswith(".json"):
            claim = json.loads(original(name))
            key = Path(claim["output"]).name
            assert key not in claims
            claims[key] = claim
    task_names = [
        name for name in entries if name.startswith("native/tasks/") and name.endswith("/task.toml")
    ]
    assert len(task_names) == 1
    result = verify_refusal(
        pipeline=json.loads(original("pipeline.json")),
        result=json.loads(original("native/result.json")),
        execution=json.loads(original("native/execution.json")),
        task=tomllib.loads(original(task_names[0]).decode()),
        claims=claims,
        paths=entries,
        log=root_original("campaign.log").decode(),
        source_hashes={name: digest(data) for name, data in selected.items()},
        upstream_sha256=upstream_hash,
    )
    result.update(
        original_campaign_log_sha256=digest(root_original("campaign.log")),
        original_upstream_source_sha256=upstream_hash,
        original_unpatched_upstream_source_sha256=raw_upstream_hash,
        original_patch_pin_sha256=PIN,
        original_factory_source_sha256={name: digest(data) for name, data in selected.items()},
    )
    return result
