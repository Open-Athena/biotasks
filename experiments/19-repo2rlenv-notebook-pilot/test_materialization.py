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
    (tmp_path / "manifest.json").write_text(
        json.dumps(
            {
                "files": [
                    {"path": "oracle.py", "bytes": 4, "sha256": hashlib.sha256(b"pass").hexdigest()}
                ]
            }
        )
    )
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


def test_new_attempt_invalidates_stale_reports_and_retains_author_only_access(
    tmp_path, monkeypatch
):
    import stat

    import materialization_remote as module

    area = tmp_path / "inspection"
    area.mkdir()
    for name in ("dependency-assets-final.json", "asset-value-hints.json", "unrelated.txt"):
        (area / name).write_text("previous attempt")
    owners = []
    monkeypatch.setattr(module.os, "chown", lambda path, uid, gid: owners.append((path, uid, gid)))
    module.reset_inspection(area)
    assert owners == [(area, 0, module.AUTHOR)]
    assert stat.S_IMODE(area.stat().st_mode) == 0o750
    assert sorted(p.name for p in area.iterdir()) == ["unrelated.txt"]
    # It is safe to reset again after a failed attempt produced no reports.
    module.reset_inspection(area)


def test_reset_does_not_recursively_delete_an_unexpected_report_directory(tmp_path, monkeypatch):
    import materialization_remote as module

    area = tmp_path / "inspection"
    area.mkdir()
    unexpected = area / "asset-value-hints.json"
    unexpected.mkdir()
    (unexpected / "evidence.txt").write_text("preserve")
    monkeypatch.setattr(module.os, "chown", lambda *args: None)
    with pytest.raises(IsADirectoryError):
        module.reset_inspection(area)
    assert (unexpected / "evidence.txt").read_text() == "preserve"


@pytest.mark.parametrize("mode", ["fresh", "finalize", "construct_with_prior"])
@pytest.mark.parametrize("remove_fixture", [False, True])
@pytest.mark.parametrize("corruption", ["none", "catalog", "hints", "hint_binding"])
def test_materialization_controller_preserves_candidate_and_checks_downloads(
    tmp_path, mode, remove_fixture, corruption
):
    import asyncio
    import json
    import time
    from types import SimpleNamespace

    from materialization_environment import binding, removal_receipt
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
        operation_coverage=[
            dict(
                operation_ids=["call-1-9"],
                role="result",
                artifact_paths=["value.txt"],
                counterpart_id=None,
                rationale="Source analysis result.",
            )
        ],
    )
    prior = tmp_path / "prior"
    prior.mkdir()
    (prior / "oracle.py").write_text("pass")
    (prior / "manifest.json").write_text(
        json.dumps(
            {
                "files": [
                    {"path": "oracle.py", "bytes": 4, "sha256": hashlib.sha256(b"pass").hexdigest()}
                ]
            }
        )
    )
    uploads = []
    calls = []
    executions = []
    catalog_downloads = []
    hint_downloads = []
    removals = (
        [
            {
                "distribution": "example",
                "path": "example/tests/expected.txt",
                "sha256": "a" * 64,
                "reason": "Synthetic worker observed an unused answer fixture",
            }
        ]
        if remove_fixture
        else []
    )
    request = {}
    catalog = {"files": [], "summary": {"priority_matches": [], "candidate_files": 0}}
    catalog_raw = (json.dumps(catalog, indent=2) + "\n").encode()
    hints_raw = b""
    controlled = {
        "status": "executed_requires_scientific_validation",
        "inputs": [item],
        "reference": [item],
        "oracle_outputs": [item],
        "environment_removal_receipt": removal_receipt({"files": []}),
        "environment": {
            "exclusions": {"files": []},
            "removal_receipt": removal_receipt({"files": []}),
            "asset_catalog": {
                "sha256": hashlib.sha256(catalog_raw).hexdigest(),
                "bytes": len(catalog_raw),
            },
            "asset_summary": catalog["summary"],
        },
    }

    async def upload(local, remote):
        uploads.append(remote)
        if remote == "/work/grading-private/materialization.json":
            request.update(json.loads(local.read_text()))

    async def download(remote, local):
        content = data
        if remote.endswith("dependency-assets-final.json"):
            catalog_downloads.append(remote)
            content = (
                b"CORRUPTED"
                if corruption == "catalog" and len(catalog_downloads) == 1
                else catalog_raw
            )
        if remote.endswith("asset-value-hints.json"):
            hint_downloads.append(remote)
            content = (
                b"CORRUPTED" if corruption == "hints" and len(hint_downloads) == 1 else hints_raw
            )
        local.write_bytes(content)

    async def command(argv, seconds, label):
        nonlocal catalog_raw, hints_raw
        assert argv[-1] == "/work/materialization_remote.py"
        assert time.time() < request["controlled_execution_deadline"] <= time.time() + 60
        executions.append(label)
        merged = request["effective_dependency_exclusions"]
        catalog["summary"]["candidate_files"] = int(not merged["files"])
        catalog_raw = (json.dumps(catalog, indent=2) + "\n").encode()
        controlled["environment_removal_receipt"] = removal_receipt(merged)
        controlled["environment"].update(
            exclusions=merged,
            removal_receipt=removal_receipt(merged),
            asset_catalog={
                "sha256": hashlib.sha256(catalog_raw).hexdigest(),
                "bytes": len(catalog_raw),
            },
        )
        hints = {
            "source": {
                "asset_catalog_sha256": hashlib.sha256(catalog_raw).hexdigest(),
                "reference_inventory_sha256": hashlib.sha256(
                    json.dumps(controlled["reference"]).encode()
                ).hexdigest(),
            },
            "findings": [{"source_text": "PRIVATE-NUMERIC-HINT"}],
            "scope": "Synthetic discovery fixture, not an isolation verdict",
        }
        if corruption == "hint_binding" and len(executions) == 1:
            hints["source"]["reference_inventory_sha256"] = "0" * 64
        hints_raw = json.dumps(hints).encode()
        controlled["environment"]["asset_value_hints"] = {
            "source": hints["source"],
            "scope": hints["scope"],
            "finding_count": len(hints["findings"]),
            "bytes": len(hints_raw),
            "sha256": hashlib.sha256(hints_raw).hexdigest(),
        }
        return {
            "exit_code": 0,
            "log": json.dumps(controlled),
        }

    async def shell(command, timeout_sec=120):
        raise AssertionError("Synthetic author needs no shell")

    async def complete(payload):
        calls.append(payload)
        if len(calls) > 3:
            raise AssertionError("Unexpected extra synthetic worker request")
        if len(calls) > 1:
            candidate["environment_review"] = {
                **binding(controlled),
                "assessment": "Synthetic observed empty candidate inventory",
                "additional_exclusions": removals,
            }
        model_input = json.loads(payload["messages"][1]["content"])
        assert model_input["source_operations"]["operations"][0]["function"] == "analyze"
        tool_names = {t["function"]["name"] for t in payload["tools"]}
        expected_tools = {"submit_artifact", "revise_artifact"}
        if mode != "finalize":
            expected_tools.add("shell")
        assert tool_names == expected_tools
        assert "response_format" not in payload
        if mode == "construct_with_prior":
            assert "Inspect the actual input keys" in payload["messages"][0]["content"]
            assert "prior_worker_draft" in payload["messages"][1]["content"]
        review_only = mode == "construct_with_prior" and len(calls) > 1
        return {
            "choices": [
                {
                    "finish_reason": "tool_calls",
                    "message": {
                        "role": "assistant",
                        "content": None,
                        "tool_calls": [
                            {
                                "id": "submit-" + str(len(calls)),
                                "type": "function",
                                "function": {
                                    "name": "revise_artifact" if review_only else "submit_artifact",
                                    "arguments": json.dumps(
                                        {
                                            "patch": {
                                                "environment_review": candidate[
                                                    "environment_review"
                                                ]
                                            }
                                        }
                                        if review_only
                                        else candidate
                                    ),
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
                    "review": "Observed scientific uncertainty",
                    "validation_handoff": "Later grader plan",
                },
                "policy": {},
                "source_evidence": {"inputs/original.py": "result = analyze(data)\n"},
                "reference_observations": {},
                "paths": {},
            },
            root=root,
            config={
                "reference_seconds": 600,
                "request_timeout_seconds": 600,
                **({"prior_author_files": str(prior)} if mode != "fresh" else {}),
                **({"authoring_mode": "construct"} if mode == "construct_with_prior" else {}),
            },
            endpoint="unused",
            credential="unused",
            deadline=time.time() + 60,
            complete=complete,
        )
    )
    assert json.loads((root / "materialize/input.json").read_text())["specification"] == {
        "task_brief": "Synthetic question",
        "review": "Observed scientific uncertainty",
    }
    assert result["oracle_executed"]
    assert len(calls) == (3 if remove_fixture else 2)
    assert len(executions) == (2 if remove_fixture or corruption != "none" else 1)
    assert (
        json.loads((root / "materialized/manifest.json").read_text())["environment"]["exclusions"][
            "files"
        ]
        == removals
    )
    assert not result["numerical_comparison_validated"]
    assert json.loads((root / "materialization-candidate.json").read_text()) == candidate
    assert (root / "materialized/reference/value.txt").read_bytes() == data
    assert "/work/grading-private/materialization.json" in uploads
    assert "/work/asset_literal_inspection.py" in uploads
    assert "/work/installed_asset_hints.py" in uploads
    # The report is an inspectable private artifact, not an unbounded tool-error
    # payload or material inserted into every model call by default.
    assert "PRIVATE-NUMERIC-HINT" not in json.dumps(calls)
    assert (root / "materialization/1/asset-value-hints.json").exists() is (corruption != "catalog")


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
