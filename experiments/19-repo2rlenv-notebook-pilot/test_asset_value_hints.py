"""Discovery evidence does not become a scientific verdict or an absence claim."""

import asyncio
import hashlib
import io
import json
import time
import zipfile

import httpx
import pytest
from asset_value_hints import build_hints, floating_literals
from grading_protocol import Review, check_review_asset_hints
from package_inspection import PackageInspection
from pydantic import ValidationError
from reference_inspection import ReferenceInspection


class RecordedPackages:
    members = staticmethod(PackageInspection.members)
    open_member = staticmethod(PackageInspection.open_member)

    def __init__(self, tmp_path, code):
        self.path = tmp_path / "recorded.whl"
        with zipfile.ZipFile(self.path, "w") as archive:
            archive.writestr("release/tests/expected.py", code)
        self.calls = []

    async def archive(self, package):
        self.calls.append(package)
        return zipfile.ZipFile(self.path)

    def remaining(self):
        pass


def inputs(tmp_path, code, files=None):
    packages = RecordedPackages(tmp_path, code)
    root = tmp_path / "outputs"
    root.mkdir()
    catalog = {}
    for name, data in (files or {"scores.csv": "id,value\na,4.9275633\nb,4.9275633\n"}).items():
        raw = data.encode()
        (root / name).write_bytes(raw)
        catalog[name] = {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}
    references = ReferenceInspection(root, catalog, time.time() + 30)
    assets = [
        {
            "distribution": "Example_Tests",
            "path": "tests/expected.py",
            "sha256": hashlib.sha256(code.encode()).hexdigest(),
        }
    ]
    return packages, references, assets


def test_final_output_matching_preserves_source_identity_and_counts_repeated_cells(tmp_path):
    code = "expected = 4.92756328\n"
    packages, references, assets = inputs(tmp_path, code)
    result = asyncio.run(build_hints(packages, references, assets, []))
    assert packages.calls == ["example-tests"]
    assert len(result["findings"]) == 1
    match = result["findings"][0]
    assert match["asset_sha256"] == assets[0]["sha256"]
    assert match["reference_sha256"] == references.catalog["scores.csv"]["sha256"]
    assert match["source_line"] == 1 and match["reference_line"] == 2
    assert match["reference_column"] == 2 and match["matching_cells"] == 2
    assert match["source_text"] == "expected = 4.92756328"
    assert match["reference_value"] == 4.9275633
    assert result["distance_is_not_grading_tolerance"]
    assert "Absence is not" in result["scope"]


def test_independent_output_branch_and_signs_are_explicit_discovery_only(tmp_path):
    packages, references, assets = inputs(
        tmp_path,
        "expected = -0.000007654321\n",
        {"first.csv": "value\n8.7654321\n", "terminal.tsv": "gene\tvalue\nZ\t0.000007654321\n"},
    )
    result = asyncio.run(build_hints(packages, references, assets, []))
    assert len(result["findings"]) == 1
    row = result["findings"][0]
    assert row["reference_path"] == "terminal.tsv"
    assert row["literal_magnitude"] == 0.000007654321
    assert row["source_text"].startswith("expected = -")


def test_comments_strings_integers_and_trivial_constants_are_coverage_gaps():
    code = b'# expected 7.123456\ntext = "7.123456"\nvalues = [0.0, 1.0, 2.0, 12e2, 1234567, 2.345678]\n'
    values = list(floating_literals(io.BytesIO(code), lambda: None))
    assert [x["literal_magnitude"] for x in values] == [2.345678]


def test_release_source_must_equal_actual_installed_asset(tmp_path):
    packages, references, assets = inputs(tmp_path, "expected = 4.9275633\n")
    assets[0]["sha256"] = "f" * 64
    result = asyncio.run(build_hints(packages, references, assets, []))
    assert result["findings"] == []
    assert result["candidates"][0]["status"] == "installed_source_identity_differs"


@pytest.mark.parametrize("same_hash", [True, False])
def test_applied_exclusion_requires_the_same_installed_file_identity(tmp_path, same_hash):
    packages, references, assets = inputs(tmp_path, "expected = 4.9275633\n")
    excluded = {**assets[0], "sha256": assets[0]["sha256"] if same_hash else "0" * 64}
    result = asyncio.run(build_hints(packages, references, assets, [excluded]))
    assert bool(result["findings"]) is not same_hash
    assert bool(packages.calls) is not same_hash


@pytest.mark.parametrize("change", ["bytes", "symlink"])
def test_changed_or_linked_reference_cannot_supply_hint_evidence(tmp_path, change):
    packages, references, assets = inputs(tmp_path, "expected = 4.9275633\n")
    path = references.root / "scores.csv"
    if change == "bytes":
        path.write_text("value\n4.9275633\n")
    else:
        path.rename(references.root / "original")
        path.symlink_to(references.root / "original")
    with pytest.raises(ValueError, match="identity changed|Linked reference"):
        asyncio.run(build_hints(packages, references, assets, []))


def test_unsupported_outputs_and_unparseable_source_are_explicit_gaps(tmp_path):
    packages, references, assets = inputs(
        tmp_path, "values = [4.9275633\n", {"results.json": '{"value": 4.9275633}'}
    )
    result = asyncio.run(build_hints(packages, references, assets, []))
    assert result["findings"] == []
    assert result["candidates"][0]["status"] == "unreadable_python_tokens"
    assert result["reference_coverage"] == [
        {"path": "results.json", "status": "unsupported_format"}
    ]


def review(assessments, decision="accept_for_packaging"):
    return Review(
        decision=decision,
        rationale="synthetic review",
        issues=[],
        asset_value_assessments=assessments,
    )


def assessment(decision="unrelated", hint="a" * 64):
    return {
        "hint_id": hint,
        "decision": decision,
        "rationale": "Different scientific input and quantity",
        "evidence": ["Recorded source provenance and computation inspected"],
    }


@pytest.mark.parametrize("rows", [[], [assessment(hint="b" * 64)], [assessment(), assessment()]])
def test_acceptance_cannot_ignore_fabricate_or_duplicate_a_supplied_hint(rows):
    with pytest.raises(ValueError, match="every supplied"):
        check_review_asset_hints(review(rows), [{"hint_id": "a" * 64}])


@pytest.mark.parametrize("decision", ["answer_exposure", "unresolved"])
def test_acceptance_cannot_override_the_workers_exposure_or_uncertainty(decision):
    rows = [assessment(decision)]
    with pytest.raises(ValueError, match="Acceptance cannot retain"):
        check_review_asset_hints(review(rows), [{"hint_id": "a" * 64}])
    check_review_asset_hints(review(rows, "blocked"), [{"hint_id": "a" * 64}])


def test_worker_can_clear_an_unrelated_numeric_coincidence_with_evidence():
    check_review_asset_hints(review([assessment()]), [{"hint_id": "a" * 64}])
    check_review_asset_hints(review([]), [])
    with pytest.raises(ValidationError, match="explicit evidence"):
        review([{**assessment(), "rationale": " "}])


def test_review_preparation_uses_bound_catalog_and_reports_missing_evidence(tmp_path):
    from review_inspection import ReviewInspection
    from test_review_inspection import snapshot

    source = snapshot(tmp_path)
    inspection = ReviewInspection(source, tmp_path / "inspection", time.time() + 30)
    asyncio.run(inspection.prepare_asset_value_hints())
    assert (
        inspection.context["asset_value_hints"]["status"] == "installed_asset_summary_unavailable"
    )
    assert (
        json.loads((inspection.root / "asset-value-hints.json").read_text())
        == (inspection.context["asset_value_hints"])
    )


def test_changed_catalog_does_not_become_observed_installed_evidence(tmp_path):
    from review_inspection import ReviewInspection
    from test_review_inspection import snapshot

    source = snapshot(tmp_path)
    name = "trial/dependency-assets-summary.json"
    path = source["directory"] / name
    path.write_text('{"priority_matches": []}')
    source["hashes"][name] = "0" * 64
    inspection = ReviewInspection(source, tmp_path / "inspection", time.time() + 30)
    with pytest.raises(ValueError, match="asset evidence identity changed"):
        asyncio.run(inspection.prepare_asset_value_hints())


@pytest.mark.parametrize("expired", [True, False])
def test_inspection_deadline_propagates_but_unavailable_release_is_a_gap(tmp_path, expired):
    packages, references, assets = inputs(tmp_path, "expected = 4.9275633\n")

    async def unavailable(package):
        if expired:
            raise TimeoutError("Original campaign deadline exhausted")
        raise httpx.ConnectError("PRIVATE source transport detail")

    packages.archive = unavailable
    if expired:
        with pytest.raises(TimeoutError):
            asyncio.run(build_hints(packages, references, assets, []))
    else:
        value = asyncio.run(build_hints(packages, references, assets, []))
        assert value["findings"] == []
        assert value["candidates"][0]["status"] == "release_source_unavailable"
        assert "PRIVATE" not in json.dumps(value)
