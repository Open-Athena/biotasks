"""Small synthetic checks for derived-input contracts and immutable sources."""

import hashlib

import pytest
from materialization_protocol import Materialization, relative_paths
from materialization_remote import inventory, verify_sources
from pydantic import ValidationError


@pytest.mark.parametrize("paths", [["../x"], ["/x"], ["."], [""], ["a//b"], ["x", "x"]])
def test_paths_do_not_escape_or_alias(paths):
    with pytest.raises(ValueError):
        relative_paths(paths)


def test_syntax_failure_is_a_repairable_schema_error():
    with pytest.raises(ValidationError):
        Materialization(
            disposition="ready",
            instruction="Synthetic task",
            input_paths=["x.txt"],
            output_paths=["y.txt"],
            derive_code="not python !",
            oracle_code="pass",
            rationale="Synthetic",
        )


def test_recovered_draft_refuses_changed_code(tmp_path):
    import json
    from task_materialization import recovered_author_files

    (tmp_path / "oracle.py").write_text("pass")
    (tmp_path / "manifest.json").write_text(json.dumps({"files": [{
        "path": "oracle.py", "bytes": 4, "sha256": hashlib.sha256(b"pass").hexdigest()
    }]}))
    assert recovered_author_files(tmp_path)["files"] == {"oracle.py": "pass"}
    (tmp_path / "oracle.py").write_text("fail")
    with pytest.raises(ValueError, match="identity"):
        recovered_author_files(tmp_path)


def test_source_corruption_and_unsafe_output_links_fail(tmp_path):
    source = tmp_path / "input.txt"
    source.write_bytes(b"original")
    manifest = {
        "files": [
            {
                "local_path": str(source),
                "bytes": 8,
                "sha256": hashlib.sha256(b"original").hexdigest(),
            }
        ]
    }
    verify_sources(manifest)
    source.write_bytes(b"changed!")
    with pytest.raises(ValueError, match="identity"):
        verify_sources(manifest)
    out = tmp_path / "outputs"
    out.mkdir()
    (out / "value.txt").write_bytes(b"1")
    assert inventory(out)[0]["bytes"] == 1
    (out / "alias").symlink_to(source)
    with pytest.raises(ValueError, match="Symlinks"):
        inventory(out)


@pytest.mark.parametrize("finalize", [False, True])
def test_materialization_controller_preserves_candidate_and_checks_downloads(tmp_path, finalize):
    import asyncio
    import json
    import time
    from types import SimpleNamespace

    from task_materialization import run_materialization

    source = tmp_path / "source"
    (source / "trial").mkdir(parents=True)
    (source / "trial/inputs-before.json").write_text('{"files": []}')
    root = tmp_path / "evidence"
    root.mkdir()
    data = b"1"
    item = {"path": "value.txt", "bytes": 1, "sha256": hashlib.sha256(data).hexdigest()}
    candidate = dict(
        disposition="ready",
        instruction="Read inputs/value.txt and write outputs/value.txt",
        input_paths=["value.txt"],
        output_paths=["value.txt"],
        derive_code="pass",
        oracle_code="pass",
        rationale="Synthetic fixture",
    )
    prior = tmp_path / "prior"
    prior.mkdir()
    (prior / "oracle.py").write_text("pass")
    (prior / "manifest.json").write_text(json.dumps({"files": [{
        "path": "oracle.py", "bytes": 4, "sha256": hashlib.sha256(b"pass").hexdigest()
    }]}))
    uploads = []

    async def upload(local, remote):
        uploads.append(remote)

    async def download(remote, local):
        local.write_bytes(data)

    async def command(argv, seconds, label):
        assert argv[-1] == "/work/materialization_remote.py"
        return {
            "exit_code": 0,
            "log": json.dumps(
                {
                    "status": "executed_requires_scientific_validation",
                    "inputs": [item],
                    "reference": [item],
                    "oracle_outputs": [item],
                }
            ),
        }

    async def shell(command, timeout_sec=120):
        raise AssertionError("Synthetic author needs no shell")

    async def complete(payload):
        if finalize:
            assert "tools" not in payload
            assert payload["response_format"]["type"] == "json_schema"
            return {"choices": [{"finish_reason": "stop", "message": {
                "role": "assistant", "content": json.dumps(candidate)
            }}]}
        return {
            "choices": [
                {
                    "finish_reason": "tool_calls",
                    "message": {
                        "role": "assistant",
                        "content": None,
                        "tool_calls": [
                            {
                                "id": "submit",
                                "type": "function",
                                "function": {
                                    "name": "submit_artifact",
                                    "arguments": json.dumps(candidate),
                                },
                            }
                        ],
                    },
                }
            ]
        }

    session = SimpleNamespace(
        snapshot={"directory": source},
        command=command,
        shell=shell,
        remote=SimpleNamespace(upload=upload, download=download),
    )
    result = asyncio.run(
        run_materialization(
            session=session,
            context={
                "specification": {
                    "task_brief": "Synthetic question",
                    "validation_handoff": "Later grader plan",
                },
                "policy": {},
                "source_evidence": {},
                "reference_observations": {},
                "paths": {},
            },
            root=root,
            config={"reference_seconds": 600, "request_timeout_seconds": 600,
                    **({"prior_author_files": str(prior)} if finalize else {})},
            endpoint="unused",
            credential="unused",
            deadline=time.time() + 60,
            complete=complete,
        )
    )
    assert json.loads((root / "materialize/input.json").read_text())["specification"] == {
        "task_brief": "Synthetic question"
    }
    assert result["oracle_executed"]
    assert not result["numerical_comparison_validated"]
    assert json.loads((root / "materialization-candidate.json").read_text()) == candidate
    assert (root / "materialized/reference/value.txt").read_bytes() == data
    assert "/work/grading-private/materialization.json" in uploads


def test_reuse_requires_verified_materialization_and_cleanup(tmp_path):
    import json

    from materialization_inputs import archive_selection

    candidate = {"disposition": "ready", "input_paths": ["x"], "output_paths": ["y"]}
    item = {"bytes": 1, "sha256": hashlib.sha256(b"1").hexdigest()}
    execution = {
        "status": "executed_requires_scientific_validation",
        "inputs": [dict(item, path="x")],
        "reference": [dict(item, path="y")],
        "oracle_outputs": [dict(item, path="y")],
    }
    result = {"status": "materialized_requires_scientific_validation", "cleanup_verified": True}
    records = []
    for name, value in [
        ("candidate.json", candidate),
        ("manifest.json", execution),
        ("result.json", result),
    ]:
        data = json.dumps(value).encode()
        (tmp_path / name).write_bytes(data)
        records.append(
            {"path": name, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
        )
    (tmp_path / "artifact-manifest.json").write_text(json.dumps({"original_small_files": records}))
    selected = archive_selection(tmp_path)
    assert {p["path"] for p in selected} == {
        "grading/materialized/inputs/x",
        "grading/materialized/reference/y",
        "grading/materialized/oracle_outputs/y",
    }
    (tmp_path / "result.json").write_text("{}")
    with pytest.raises(ValueError, match="identity changed"):
        archive_selection(tmp_path)
