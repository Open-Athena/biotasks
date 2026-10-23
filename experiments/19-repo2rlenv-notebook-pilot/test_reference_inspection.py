"""Reference-file identity, read-only boundary and specification tool integration."""

import asyncio
import hashlib
import json
import time
from copy import deepcopy

import pytest
from reference_inspection import ReferenceInspection, reference_catalog


def record(path, content):
    return {"path": path, "sha256": hashlib.sha256(content).hexdigest(), "bytes": len(content)}


def inspector(tmp_path, content=b"FORMAT 1\nNAME observed\n", name="nested/result.txt"):
    output = tmp_path / name
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(content)
    catalog = reference_catalog([record(name, content)])
    return ReferenceInspection(tmp_path, catalog["files"], time.time() + 60)


def test_full_identity_and_requested_lines_without_execution(tmp_path):
    content = b"raise RuntimeError('never execute')\n" + b"value\n" * 310
    source = inspector(tmp_path, content, "result.py")
    result = json.loads(asyncio.run(source.read_reference_file("result.py", 301, 305)))
    assert result["sha256"] == hashlib.sha256(content).hexdigest()
    assert result["bytes"] == len(content) and result["total_lines"] == 311
    assert result["lines"] == [{"line": n, "text": "value"} for n in range(301, 306)]
    assert (tmp_path / "result.py").read_bytes() == content
    assert sorted(p.name for p in tmp_path.iterdir()) == ["result.py"]


def test_compact_single_line_has_explicit_windows_and_allows_full_read(tmp_path):
    text = json.dumps({"records": ["évidence" * 1000, "terminal"]}, ensure_ascii=False)
    content = text.encode()
    source = inspector(tmp_path, content, "compact.json")
    first = json.loads(asyncio.run(source.read_reference_file("compact.json")))
    assert first["lines"] == [{"line": 1, "text": text[:1000]}]
    assert first["line_characters"] == {"1": len(text)} and first["sliced_lines"] == [1]
    assert first["bytes"] == len(content) and first["total_lines"] == 1
    second = json.loads(
        asyncio.run(source.read_reference_file("compact.json", start_column=1001, end_column=None))
    )
    assert first["lines"][0]["text"] + second["lines"][0]["text"] == text
    assert second["sha256"] == first["sha256"] and second["sliced_lines"] == [1]
    full = json.loads(asyncio.run(source.read_reference_file("compact.json", end_column=None)))
    assert full["lines"] == [{"line": 1, "text": text}] and full["sliced_lines"] == []


@pytest.mark.parametrize(
    "columns",
    [
        {"start_column": 0},
        {"end_column": True},
        {"start_column": True},
        {"start_column": 3, "end_column": 2},
    ],
)
def test_invalid_column_window_returns_no_content(tmp_path, columns):
    source = inspector(tmp_path)
    value = json.loads(
        asyncio.run(source.handlers["read_reference_file"](path="nested/result.txt", **columns))
    )
    assert "error" in value and "lines" not in value


@pytest.mark.parametrize("change", ["same_size", "different_size", "missing", "directory"])
def test_changed_unrequested_bytes_or_unavailable_file_rejected(tmp_path, change):
    source = inspector(tmp_path)
    target = tmp_path / "nested/result.txt"
    if change == "same_size":
        target.write_bytes(target.read_bytes().replace(b"observed", b"altered!"))
    elif change == "different_size":
        with target.open("ab") as stream:
            stream.write(b"extra\n")
    else:
        target.unlink()
        if change == "directory":
            target.mkdir()
    reply = json.loads(
        asyncio.run(source.handlers["read_reference_file"](path="nested/result.txt", end_line=1))
    )
    assert "error" in reply and "lines" not in reply


@pytest.mark.parametrize(
    "path", ["../outside", "/etc/passwd", "nested/../result.txt", "./a", "a//b", ""]
)
def test_unsafe_catalog_paths_rejected(path):
    with pytest.raises(ValueError, match="reference identity"):
        reference_catalog([record(path, b"value")])


def test_duplicate_catalog_identity_rejected():
    item = record("output.txt", b"value")
    with pytest.raises(ValueError, match="reference identity"):
        reference_catalog([item, item])


@pytest.mark.parametrize("leaf_link", [True, False])
def test_symlinks_are_not_followed_even_with_matching_identity(tmp_path, leaf_link):
    source = inspector(tmp_path)
    original = tmp_path / "nested/result.txt"
    if leaf_link:
        original.rename(tmp_path / "other.txt")
        original.symlink_to(tmp_path / "other.txt")
    else:
        (tmp_path / "nested").rename(tmp_path / "real")
        (tmp_path / "nested").symlink_to(tmp_path / "real", target_is_directory=True)
    reply = json.loads(
        asyncio.run(source.handlers["read_reference_file"](path="nested/result.txt"))
    )
    assert "error" in reply and "lines" not in reply


@pytest.mark.parametrize("content", [b"binary\0data", b"\x89PNG\xff", b"header\n\xff"])
def test_binary_or_invalid_utf8_remains_explicit_gap(tmp_path, content):
    source = inspector(tmp_path, content)
    reply = json.loads(
        asyncio.run(source.handlers["read_reference_file"](path="nested/result.txt"))
    )
    assert "error" in reply and "lines" not in reply


@pytest.mark.parametrize(
    "arguments",
    [
        {"path": "unlisted"},
        {"path": "nested/result.txt", "start_line": 0},
        {"path": "nested/result.txt", "end_line": True},
        {"path": "nested/result.txt", "start_line": 2, "end_line": 1},
    ],
)
def test_invalid_tool_arguments_return_no_content(tmp_path, arguments):
    source = inspector(tmp_path)
    reply = json.loads(asyncio.run(source.handlers["read_reference_file"](**arguments)))
    assert "error" in reply and "lines" not in reply


def test_expired_campaign_is_not_converted_to_retryable_tool_error(tmp_path):
    source = inspector(tmp_path)
    source.deadline = time.time() - 1
    with pytest.raises(TimeoutError):
        asyncio.run(source.handlers["read_reference_file"](path="nested/result.txt"))


@pytest.mark.parametrize("inspect_packages", [False, True])
@pytest.mark.parametrize("recover_context", [False, True])
def test_specification_worker_reads_recorded_reference_then_submits(
    tmp_path, inspect_packages, recover_context
):
    from run_specification import run
    from specification_inputs import INPUT_FILES, specification_context

    reference = tmp_path / "reference"
    reference.mkdir()
    content = b"FORMAT 1" + (b" observed" * 3000 if recover_context else b"") + b"\nNAME observed\n"
    output = record("result.txt", content)
    values = {path: {} if path.endswith(".json") else "" for path in INPUT_FILES}
    values.update(
        {
            "trial/uv.lock": "package = []\n",
            "inputs/plan.json": {"artifacts": [{"path": "result.txt"}]},
            "trial/result.json": {
                "status": "reference_executed",
                "execution": {"exit_code": 0, "timed_out": False},
                "artifacts": {"artifacts": [{**output, "exists": True}]},
            },
            "result.json": {"status": "reference_executed_requires_review"},
            "output-audit.json": {
                "outputs": [
                    {
                        "file": "result.txt",
                        "sha256": output["sha256"],
                        "bytes": len(content),
                        "download_hash_verified": True,
                    }
                ]
            },
        }
    )
    manifest = []
    for path, value in values.items():
        target = reference / path
        target.parent.mkdir(parents=True, exist_ok=True)
        raw = (json.dumps(value) if path.endswith(".json") else value).encode()
        target.write_bytes(raw)
        manifest.append(record(path, raw))
    (reference / "artifact-manifest.json").write_text(json.dumps({"files": manifest}))
    (reference / "trial/outputs").mkdir()
    (reference / "trial/outputs/result.txt").write_bytes(content)
    policy = tmp_path / "policy.json"
    policy.write_text("{}")
    context = specification_context(
        reference, {}, inspect_reference=True, inspect_packages=inspect_packages
    )
    assert context["reference_inspection"]["files"] == {
        "result.txt": {k: output[k] for k in ("sha256", "bytes")}
    }
    assert "No tools in this pass" not in context["evidence_boundary"]
    input_file = tmp_path / "input.json"
    input_file.write_text(json.dumps(context))
    calls = []

    async def complete(payload):
        calls.append(deepcopy(payload))
        names = {item["function"]["name"] for item in payload["tools"]}
        expected = {"read_reference_file", "submit_artifact", "revise_artifact"}
        if inspect_packages:
            expected.update({"list_package_files", "search_package", "read_package_file"})
        assert names == expected
        if len(calls) == 1:
            name, args = (
                "read_reference_file",
                {
                    "path": "result.txt",
                    "end_line": 1,
                    "end_column": None,
                },
            )
        else:
            if len(calls) == 2:
                reply = json.loads(payload["messages"][-1]["content"])
                assert reply["sha256"] == output["sha256"]
                assert reply["lines"] == [{"line": 1, "text": content.splitlines()[0].decode()}]
                if recover_context:

                    class Rejected(Exception):
                        status_code = 400
                        body = {"error": {"message": "maximum context length exceeded"}}

                    raise Rejected()
            else:
                assert payload["messages"][:2] == calls[0]["messages"]
                assert "read-only inspection stage" in payload["messages"][-1]["content"]
                assert not any(message.get("tool_calls") for message in payload["messages"])
            name, args = (
                "submit_artifact",
                {
                    "disposition": "needs_evidence",
                    "review": "Observed format header; scientific comparisons unverified",
                    "task_brief": "",
                    "validation_handoff": "Independent execution needed",
                },
            )
        return {
            "choices": [
                {
                    "finish_reason": "tool_calls",
                    "message": {
                        "role": "assistant",
                        "content": None,
                        "tool_calls": [
                            {
                                "id": str(len(calls)),
                                "type": "function",
                                "function": {"name": name, "arguments": json.dumps(args)},
                            }
                        ],
                    },
                }
            ]
        }

    config = {
        "entrypoint": "run_specification.py",
        "reasoning_effort": "high",
        "inspect_reference": True,
        "inspect_packages": inspect_packages,
        "output_format": "tools",
        "max_requests": None,
        "reference_directory": str(reference),
        "policy_file": str(policy),
        "input_file": str(input_file),
        "request_timeout_seconds": 60,
    }
    root = tmp_path / "specification"
    asyncio.run(
        run(
            config,
            root=root,
            endpoint="unused",
            credential="unused",
            deadline=time.time() + 60,
            complete=complete,
        )
    )
    assert len(calls) == (3 if recover_context else 2)
    result = json.loads((root / "result.json").read_text())
    assert result["reference_inspection_enabled"]
    assert result["package_inspection_enabled"] is inspect_packages
    assert not result["scientific_analysis_executed"] and not result["construction_run"]
    assert (reference / "trial/outputs/result.txt").read_bytes() == content
    assert (root / "specify/artifact-stage/trace/1/tool-result.json").exists()
    if recover_context:
        failure = json.loads((root / "specify/artifact-stage/trace/2/failure.json").read_text())
        assert failure["failure_category"] == "provider_context_length"
        assert result["request_states"] == {"response_received": 2, "http_error_received": 1}
        assert result["model_request_slots_used"] == 3
