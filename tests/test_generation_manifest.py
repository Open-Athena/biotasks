"""Offline boundary tests; synthetic cohort descriptors are not discovery data."""

import copy
import socket
import subprocess
import urllib.request
from pathlib import Path

import pytest

from biotasks.generation import planning as flow
from biotasks.generation import source
from biotasks.validation import planning
from biotasks.validation.files import (
    ValidationError,
    inventory,
    json_sha,
    read_json,
    sha,
    write_json,
)


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
    native_source = tmp_path / "source"
    native_source.mkdir()
    (native_source / "LICENSE").write_text("Synthetic source fixture, never imported\n")
    rows = [
        {
            "path": "LICENSE",
            "bytes": (native_source / "LICENSE").stat().st_size,
            "sha256": sha(native_source / "LICENSE"),
            "git_blob": "0" * 40,
        }
    ]
    acquisition = tmp_path / "source-manifest.json"
    write_json(acquisition, {"revision": planning.UPSTREAM, "files": rows})
    monkeypatch.setattr(source, "specification", lambda: ({"files": rows}, {}))
    extras = tmp_path / "extras"
    extras.mkdir()
    (extras / "writer.py").write_text("# Synthetic, never imported\n")
    monkeypatch.setattr(source, "writer_inventory", lambda: inventory(extras))
    quote = tmp_path / "quote.json"
    write_json(
        quote,
        {
            "data": {
                "endpoints": [
                    {
                        "context_length": 1000000,
                        "pricing": {"prompt": "0.000003", "completion": "0.000015"},
                    }
                ]
            }
        },
    )
    backend = tmp_path / "iris.yaml"
    backend.write_text("Synthetic backend, never connected\n")
    notice = tmp_path / "notices"
    notice.mkdir()
    (notice / "LICENSE").write_text("Synthetic fixture notice; not external biological input\n")
    manifest = {
        "schema_version": 1,
        "id": "fixture",
        "repo2rlenv_revision": planning.UPSTREAM,
        "validation_code_identity": planning.code_identity(),
        "source": {
            "directory": directory(native_source),
            "acquisition": ref(acquisition),
            "extra_modules": directory(extras),
        },
        "price_quote": ref(quote),
        "backend": {"type": "iris", "config": str(backend), "network": "synthetic-network"},
        "backend_config": ref(backend),
        "client_profile": {"synthetic": True},
        "budget_ledger": str(tmp_path / "unused-budget.json"),
        "archive": {"kind": "local"},
        "cases": [],
    }
    for identity, repo, count in (
        ("metabolism", "opencobra/cobrapy", 2),
        ("single-cell", "scverse/anndata", 1),
        ("empty", "synthetic/empty", 0),
    ):
        native = {
            "repo": {"url": "https://github.com/" + repo, "ref": "a" * 40, "access": "public"},
            "pipeline": {
                "name": "pr_runtime",
                "options": {"limit": 50, "since": "2026-10-12", "until": "2026-10-12"},
            },
            "llm": flow.LLM,
            "bootstrap": flow.BOOTSTRAP,
            "auth": {"use_gh_cli": False, "use_hf_cli": False},
            "output": {"destination": "/work/outputs/raw"},
        }
        candidates = {
            "repo": repo,
            "upstream_revision": planning.UPSTREAM,
            **native["pipeline"]["options"],
            "candidates": [
                {
                    "number": number + 1,
                    "state": "MERGED",
                    "base_sha": "a" * 40,
                    "head_sha": "b" * 40,
                }
                for number in range(count)
            ],
        }
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
            manifest["validation_code_identity"] = "0" * 64
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
    from biotasks.generation import manifest_handoff

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


@pytest.mark.parametrize("ready", [False, True])
def test_manifest_wait_hint_uses_actual_generation_stage_evidence(cohort, monkeypatch, ready):
    path, output, manifest = cohort
    flow.prepare(path, output)
    runtime, _, _ = flow.adapter(manifest)

    def observation(root, once):
        assert root == output / "metabolism" and once is True
        if ready:
            write_json(
                root / "runs/generation/submission_recorded.json", {"stage": "submission_recorded"}
            )
        return {"state": "recovering:submission_recorded"}

    monkeypatch.setattr(runtime, "run", observation)
    result = flow.advance(path, output, allow_generation=True)
    assert result["state"] == "recovering:submission_recorded"
    assert result["wait"] is (not ready)


@pytest.mark.parametrize("setting", [False, True])
def test_official_filter_survives_manifest_and_worker_guard_with_caps_unchanged(cohort, setting):
    from biotasks.generation import resources

    path, output, manifest = cohort
    case = manifest["cases"][0]
    config_path = Path(case["native_config"]["path"])
    candidates_path = Path(case["candidates"]["path"])
    config = read_json(config_path)
    candidates = read_json(candidates_path)
    config["pipeline"]["options"]["require_new_test_funcs"] = setting
    candidates["require_new_test_funcs"] = setting
    write_json(config_path, config)
    write_json(candidates_path, candidates)
    case["native_config"] = ref(config_path)
    case["candidates"] = ref(candidates_path)
    write_json(path, manifest)
    flow.prepare(path, output)
    planned = read_json(output / "metabolism/plan.json")
    assert planned["group"]["resources"] == flow.RESOURCES
    assert planned["model_budget"]["actual_stop_usd"] == "5"
    payload = output / "metabolism/payload"
    frozen = read_json(payload / "native-config.json")
    expected = read_json(payload / "reference-candidates.json")
    assert frozen["pipeline"]["options"]["require_new_test_funcs"] is setting
    # The exact same bundled module is used by the actual worker before GH or model calls.
    worker_guard = resources.option_policy()
    assert worker_guard.matches(frozen["pipeline"]["options"], expected)
    expected["require_new_test_funcs"] = not setting
    assert not worker_guard.matches(frozen["pipeline"]["options"], expected)
    expected["require_new_test_funcs"] = int(setting)
    assert not worker_guard.matches(frozen["pipeline"]["options"], expected)


def test_targeting_policy_is_explicit_frozen_payload_metadata(cohort):
    from biotasks.generation import resources

    path, output, manifest = cohort
    manifest["cases"][0]["targeting_policy"] = "workspace-python-v1"
    write_json(path, manifest)
    flow.prepare(path, output)
    payload = output / "metabolism/payload"
    assert read_json(payload / "family.json")["targeting_policy"] == "workspace-python-v1"
    assert read_json(output / "single-cell/payload/family.json")["targeting_policy"] is None
    assert (payload / "python_targeting.py").read_bytes() == resources.assets()[
        "python_targeting.py"
    ]
    planned = read_json(output / "metabolism/plan.json")
    assert "python_targeting.py" not in planned["reused_baseline_sha256"]
    assert "option_policy.py" not in planned["reused_baseline_sha256"]
    assert planned["group"]["resources"] == flow.RESOURCES


@pytest.mark.parametrize("policy", [True, "unknown", {"override": "anything"}])
def test_unknown_targeting_policy_rejects_before_planning(cohort, policy):
    path, output, manifest = cohort
    manifest["cases"][0]["targeting_policy"] = policy
    write_json(path, manifest)
    with pytest.raises(ValidationError, match="Unknown targeting policy"):
        flow.prepare(path, output)
    assert not output.exists()
