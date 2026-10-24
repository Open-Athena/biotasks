"""Offline boundary tests; synthetic cohort descriptors are not discovery data."""

import copy
import socket
import subprocess
import sys
import urllib.request
from pathlib import Path

import pytest
from biotasks.validation import planning
from biotasks.validation.files import (
    ValidationError,
    inventory,
    json_sha,
    read_json,
    sha,
    write_json,
)

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import manifest_flow as flow  # noqa: E402

BASE = ROOT.parents[3]
REFERENCE = BASE / ".research-worktrees/45/experiments/45-generation-handoff"


def ref(path):
    return {"path": str(path), "sha256": sha(path)}


def directory(path):
    return {"path": str(path), "inventory_sha256": json_sha(inventory(path))}


@pytest.fixture
def cohort(tmp_path, monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("Offline manifest operation attempted external execution")

    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr(socket, "getaddrinfo", forbidden)
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    monkeypatch.setattr(urllib.request, "urlopen", forbidden)
    source = read_json(REFERENCE / "historical-handoff-config.json")
    original = read_json(REFERENCE / "inputs-private/generation-002/plan.json")
    infrastructure = BASE / "experiments/28-catalogued-fields"
    notice = tmp_path / "notices"
    notice.mkdir()
    (notice / "LICENSE").write_text("Synthetic fixture notice; not external biological input\n")
    manifest = {
        "schema_version": 1,
        "id": "synthetic-cohort",
        "repo2rlenv_revision": planning.UPSTREAM,
        "validation_code_identity": planning.code_identity(),
        "adapter": {
            "directory": str(REFERENCE),
            "files": {name: sha(REFERENCE / name) for name in flow.ADAPTER_FILES},
        },
        "infrastructure": {
            name: ref(
                infrastructure / ("history-wide/cost_guard.py" if name == "cost_guard.py" else name)
            )
            for name in flow.ASSETS
        },
        "source": {
            "directory": directory(Path(source["upstream_source"])),
            "acquisition": ref(Path(source["upstream_manifest"])),
            "extra_modules": directory(Path(source["upstream_extra_modules"])),
        },
        "price_quote": ref(REFERENCE / "inputs-private/generation-002/price-quote.json"),
        "backend": original["backend"],
        "backend_config": ref(Path(original["backend"]["config"])),
        "client_profile": original["client_profile"],
        "budget_ledger": str(tmp_path / "unused-budget.json"),
        "archive": {"kind": "local"},
        "cases": [],
    }
    for identity, repo, count in (
        ("metabolism", "opencobra/cobrapy", 2),
        ("single-cell", "scverse/anndata", 1),
        ("empty", "synthetic/empty", 0),
    ):
        native = read_json(REFERENCE / "proposed-native-config.json")
        native["repo"]["url"] = "https://github.com/" + repo
        candidates = read_json(REFERENCE / "reference-candidates.json")
        candidates["repo"] = repo
        candidates["candidates"] = [
            dict(candidates["candidates"][0], number=number + 1) for number in range(count)
        ]
        config_path, candidates_path = (
            tmp_path / (identity + "-native.json"),
            tmp_path / (identity + "-prs.json"),
        )
        write_json(config_path, native)
        write_json(candidates_path, candidates)
        manifest["cases"].append(
            {
                "id": identity,
                "run_id": "synthetic-" + identity,
                "mode": "fresh",
                "native_config": ref(config_path),
                "candidates": ref(candidates_path),
                "notices": directory(notice),
                "publication": {"eligible": False},
            }
        )
    path = tmp_path / "manifest.json"
    write_json(path, manifest)
    return path, tmp_path / "planned", manifest


def test_multiple_repositories_and_multiple_or_zero_candidates(cohort):
    path, output, manifest = cohort
    result = flow.prepare(path, output)
    assert [row["candidate_count"] for row in result["cases"]] == [2, 1, 0]
    assert result["planning_model_calls"] == result["planning_remote_jobs"] == 0
    assert result["cases"][2]["state"] == "skipped_zero_candidates"
    assert not (output / "empty").exists()
    runtime, _, _ = flow.adapter(manifest)
    for identity in ("metabolism", "single-cell"):
        plan = runtime.verify(output / identity)
        assert plan["group"]["resources"] == flow.RESOURCES
        assert plan["model_budget"]["actual_stop_usd"] == "5"
        native = read_json(output / identity / "native-config.json")
        assert native["llm"] == flow.LLM and native["bootstrap"] == flow.BOOTSTRAP
    assert flow.advance(path, output)["state"] == "generation_not_admitted"


def test_completed_planning_is_byte_inert(cohort):
    path, output, _ = cohort
    original = flow.prepare(path, output)
    before = inventory(output)
    assert flow.prepare(path, output) == original
    assert inventory(output) == before


@pytest.mark.parametrize(
    "kind", ["native", "source", "notices", "adapter", "manifest", "case-plan"]
)
def test_drift_fails_before_admission(cohort, kind):
    path, output, manifest = cohort
    flow.prepare(path, output)
    if kind == "native":
        target = Path(manifest["cases"][0]["native_config"]["path"])
        target.write_text(target.read_text() + " ")
    elif kind == "notices":
        (Path(manifest["cases"][0]["notices"]["path"]) / "LICENSE").write_text("changed")
    elif kind in {"source", "adapter"}:
        if kind == "source":
            manifest["source"]["directory"]["inventory_sha256"] = "0" * 64
        else:
            manifest["adapter"]["files"]["generation_entry.py"] = "0" * 64
        write_json(path, manifest)
    elif kind == "manifest":
        manifest["cases"][0]["run_id"] = "replacement-id"
        write_json(path, manifest)
    else:
        frozen = read_json(output / "manifest-plan.json")
        frozen["cases"][0]["state"] = "skipped_zero_candidates"
        write_json(output / "manifest-plan.json", frozen)
    with pytest.raises(ValidationError):
        flow.advance(path, output)


@pytest.mark.parametrize(
    "change", ["model", "budget", "duplicate", "repo", "limit", "notice-review"]
)
def test_scope_changes_rejected(cohort, change):
    path, output, manifest = cohort
    case = manifest["cases"][0]
    if change in {"model", "budget", "repo", "limit"}:
        native_path = Path(case["native_config"]["path"])
        native = read_json(native_path)
        if change == "model":
            native["llm"]["model"] = "unapproved"
        elif change == "budget":
            native["bootstrap"]["max_iterations"] = 21
        elif change == "repo":
            native["repo"]["url"] = "https://github.com/other/repo"
        else:
            native["pipeline"]["options"]["limit"] = 500
        write_json(native_path, native)
        case["native_config"] = ref(native_path)
    elif change == "duplicate":
        manifest["cases"].append(copy.deepcopy(case))
    else:
        case["publication"] = {"eligible": True}
    write_json(path, manifest)
    with pytest.raises(ValidationError):
        flow.prepare(path, output)
    assert not output.exists()


def test_interrupted_planning_is_retained_not_admitted(cohort):
    path, output, _ = cohort
    staging = output.with_name(output.name + ".staging")
    staging.mkdir()
    (staging / "partial").write_text("preserve interrupted evidence")
    with pytest.raises(ValidationError, match="Interrupted planning"):
        flow.prepare(path, output)
    assert (staging / "partial").read_text() == "preserve interrupted evidence"
    assert not output.exists()


def test_zero_exports_do_not_import_source_or_plan_controls(cohort, monkeypatch):
    import manifest_handoff

    _, output, manifest = cohort
    case = manifest["cases"][0]
    runtime, finish, handoff = flow.adapter(manifest)
    monkeypatch.setattr(
        handoff, "source_api", lambda *args: pytest.fail("No exporter on zero output")
    )
    ready = {
        "state": "ready",
        "plan": {"backend": manifest["backend"], "budget_ledger": manifest["budget_ledger"]},
        "readback": {
            "exported_tasks": [],
            "model_billing": {"complete": True, "known_actual_usd": "0.1"},
        },
        "directory": output / "unused",
        "binding": {"synthetic": True},
    }
    result = manifest_handoff.prepare_handoff(manifest, case, ready, output)
    assert result["state"] == "zero_exports" and result["native_control_jobs"] == 0
    before = inventory(output)
    assert manifest_handoff.prepare_handoff(manifest, case, ready, output) == result
    assert inventory(output) == before


@pytest.mark.parametrize("terminal", ["held", "in_progress", "waiting_for_existing_generation"])
def test_serial_gate_does_not_start_later_case(cohort, monkeypatch, terminal):
    path, output, manifest = cohort
    flow.prepare(path, output)
    runtime, _, _ = flow.adapter(manifest)
    calls = []

    def pending(root, once):
        calls.append(root)
        return {"state": terminal}

    monkeypatch.setattr(runtime, "run", pending)
    assert flow.advance(path, output, allow_generation=True)["state"] == terminal
    assert calls == [output / "metabolism"]
