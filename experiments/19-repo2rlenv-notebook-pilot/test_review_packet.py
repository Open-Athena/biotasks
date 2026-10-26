"""File-backed review must preserve evidence and never acquire execution rights."""

import asyncio
import copy
import json
import time

import pytest
from review_packet import ReviewPacket, encode


def context():
    return {
        "policy": {"offline": True},
        "specification": {"task_brief": "Compute the scientific outputs"},
        "candidate": {
            "grader_code": "raise RuntimeError('NEVER EXECUTE')\n",
            "checks": [{"id": "effect", "required": True}],
        },
        "controls": [{"passed_control": False, "output": "π\t測定\n", "value": -0.0}],
        "source_evidence": {"inputs/original.py": "analysis(data)\n", "a~b/c": "literal source"},
        "asset_value_hints": {
            "findings": [{"hint_id": "a" * 64, "source_text": "private expected value"}]
        },
        "control_summary": {"passed": 0, "total": 1},
        "diagnostics": None,
    }


def packet(tmp_path, data=None):
    return ReviewPacket(tmp_path / "packets", data or context(), time.time() + 30)


def read(value, **args):
    return json.loads(asyncio.run(value.handlers["read_review_evidence"](**args)))


def test_complete_input_roundtrips_without_summarizing_programs_controls_or_hints(tmp_path):
    original = context()
    before = copy.deepcopy(original)
    value = packet(tmp_path, original)
    assert value.reconstruct() == original == before
    assert encode(value.reconstruct()) == encode(original)
    assert set(value.model_context["review_evidence"]["fields"]) == set(original)
    assert value.model_context["policy"] == original["policy"]
    assert value.model_context["specification"] == original["specification"]
    assert "candidate" not in value.model_context and "controls" not in value.model_context
    assert "private expected value" not in json.dumps(value.model_context)
    assert "NEVER EXECUTE" not in json.dumps(value.model_context)
    assert (
        read(value, field="candidate", pointer="/grader_code")["lines"][0]["text"]
        == before["candidate"]["grader_code"].strip()
    )
    assert read(value, field="controls", pointer="/0/passed_control")["lines"][0]["text"] == "false"
    original["controls"][0]["passed_control"] = True
    assert value.reconstruct() == before


def test_json_pointer_navigation_and_string_windows_preserve_original_quotes(tmp_path):
    value = packet(tmp_path)
    assert read(value, field="candidate", view="keys")["keys"] == list(context()["candidate"])
    assert read(value, field="controls", view="keys")["length"] == 1
    result = read(
        value, field="source_evidence", pointer="/inputs~1original.py", start_column=3, end_column=8
    )
    assert result["lines"] == [{"line": 1, "text": "alysis", "full_line_characters": 14}]
    assert (
        read(value, field="source_evidence", pointer="/a~0b~1c")["lines"][0]["text"]
        == "literal source"
    )
    assert (
        read(value, field="controls", pointer="/0/output", end_column=None)["lines"][0]["text"]
        == "π\t測定"
    )


@pytest.mark.parametrize(
    "args",
    [
        {"field": "../outside"},
        {"field": "controls", "pointer": "/01"},
        {"field": "controls", "pointer": "/-1"},
        {"field": "controls", "pointer": "/9"},
        {"field": "candidate", "pointer": "grader_code"},
        {"field": "candidate", "pointer": "/~2"},
        {"field": "candidate", "pointer": "/absent"},
        {"field": "candidate", "pointer": "/grader_code/x"},
        {"field": "candidate", "start_line": 0},
        {"field": "candidate", "end_column": 0},
        {"field": "candidate", "start_line": True},
        {"field": "candidate", "view": "execute"},
        {"field": "diagnostics", "view": "keys"},
    ],
)
def test_invalid_selectors_or_windows_return_an_evidence_gap_without_content(tmp_path, args):
    response = read(packet(tmp_path), **args)
    assert response["error"] == "review_evidence_unavailable"
    assert "lines" not in response and "keys" not in response


@pytest.mark.parametrize(
    "change", ["document", "document_link", "root_link", "manifest", "manifest_link"]
)
def test_modified_or_linked_packets_cannot_supply_review_evidence(tmp_path, change):
    value = packet(tmp_path)
    path = value.root / value.catalog["candidate"]["path"]
    if change == "document":
        path.chmod(0o600)
        path.write_text('{"grader_code": "fabricated"}')
    elif change == "document_link":
        path.unlink()
        path.symlink_to(value.root / value.catalog["controls"]["path"])
    elif change == "root_link":
        original = value.root.with_name("moved")
        value.root.rename(original)
        value.root.symlink_to(original, target_is_directory=True)
    else:
        path = value.root / "manifest.json"
        path.chmod(0o600)
        path.unlink()
        if change == "manifest":
            path.write_text("{}")
        else:
            path.symlink_to(value.root / value.catalog["candidate"]["path"])
    assert "lines" not in read(value, field="candidate")
    with pytest.raises((ValueError, OSError)):
        value.reconstruct()


def test_same_context_reuses_exact_packet_but_changed_context_gets_a_new_identity(tmp_path):
    first = packet(tmp_path)
    again = packet(tmp_path)
    assert again.root == first.root and again.manifest_sha256 == first.manifest_sha256
    revised = context()
    revised["controls"][0]["passed_control"] = True
    later = packet(tmp_path, revised)
    assert later.root != first.root
    assert not first.reconstruct()["controls"][0]["passed_control"]
    assert later.reconstruct()["controls"][0]["passed_control"]


def test_recorded_packet_opens_without_writing_or_recreating_evidence(tmp_path):
    value = packet(tmp_path)
    before = {p: (p.read_bytes(), p.stat().st_mode) for p in value.root.iterdir()}
    restored = ReviewPacket.open_recorded(
        value.root.parent, value.model_context["review_evidence"], deadline=time.time() + 30
    )
    assert restored.reconstruct() == context()
    assert before == {p: (p.read_bytes(), p.stat().st_mode) for p in value.root.iterdir()}


@pytest.mark.parametrize(
    "change", ["descriptor", "index", "missing", "manifest", "document", "linked", "escape"]
)
def test_recorded_packet_refuses_changed_missing_linked_or_escaping_evidence(tmp_path, change):
    import hashlib

    value = packet(tmp_path)
    descriptor = copy.deepcopy(value.model_context["review_evidence"])
    document = value.root / value.catalog["candidate"]["path"]
    if change == "descriptor":
        descriptor["context_sha256"] = "../outside"
    elif change == "index":
        descriptor["fields"]["candidate"]["bytes"] += 1
    elif change == "missing":
        document.unlink()
    elif change == "document":
        document.chmod(0o600)
        document.write_text("{}")
    elif change == "linked":
        document.unlink()
        document.symlink_to(value.root / value.catalog["controls"]["path"])
    else:
        manifest = value.root / "manifest.json"
        manifest.chmod(0o600)
        if change == "manifest":
            manifest.write_text("{}")
        else:
            data = json.loads(manifest.read_text())
            data["fields"]["candidate"]["path"] = "../outside.json"
            manifest.write_text(json.dumps(data))
            descriptor["manifest_sha256"] = hashlib.sha256(manifest.read_bytes()).hexdigest()
    with pytest.raises((ValueError, OSError)):
        restored = ReviewPacket.open_recorded(
            value.root.parent, descriptor, deadline=time.time() + 30
        )
        restored.reconstruct()


def test_original_object_member_order_is_preserved_in_documents_and_packet_identity(tmp_path):
    original = context()
    first = packet(tmp_path, original)
    reordered = dict(reversed(list(original.items())))
    second = packet(tmp_path, reordered)
    assert list(first.reconstruct()) == list(original)
    assert list(second.reconstruct()) == list(reordered)
    assert second.context_sha256 != first.context_sha256
    assert list(first.reconstruct()["candidate"]) == list(original["candidate"])


def test_deadline_is_shared_and_packet_tools_cannot_execute_or_write(tmp_path):
    value = packet(tmp_path)
    assert set(value.handlers) == {"read_review_evidence"}
    assert {x["function"]["name"] for x in value.tools} == set(value.handlers)
    value.deadline = time.time() - 1
    with pytest.raises(TimeoutError):
        read(value, field="candidate")
    with pytest.raises(TimeoutError):
        ReviewPacket(tmp_path / "expired", context(), time.time() - 1)


def test_initial_input_does_not_repeat_long_generated_evidence_but_all_bytes_are_readable(tmp_path):
    original = context()
    original["candidate"]["grader_code"] = "# explanatory evidence\n" * 20000
    original["controls"] = [{"passed_control": False, "log": "recorded observation\n" * 10000}]
    value = packet(tmp_path, original)
    assert len(encode(value.model_context)) < len(encode(original))
    assert value.reconstruct() == original
    result = read(
        value,
        field="candidate",
        pointer="/grader_code",
        start_line=19999,
        end_line=20000,
        end_column=None,
    )
    assert result["total_lines"] == 20000 and len(result["lines"]) == 2


def test_review_inspection_exposes_packet_only_to_its_readonly_review_tools(tmp_path):
    from review_inspection import ReviewInspection
    from test_review_inspection import snapshot

    inspection = ReviewInspection(snapshot(tmp_path), tmp_path / "inspection", time.time() + 30)
    assert "read_review_evidence" not in inspection.handlers
    result = inspection.prepare_review_context(context())
    assert result == inspection.packet.model_context
    response = json.loads(
        asyncio.run(
            inspection.handlers["read_review_evidence"](
                field="controls", pointer="/0/passed_control"
            )
        )
    )
    assert response["lines"][0]["text"] == "false"
    assert {t["function"]["name"] for t in inspection.tools} == set(inspection.handlers)
