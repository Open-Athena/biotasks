"""Synthetic inspection/provenance failures and coverage admission boundaries."""

import hashlib
import io
import json
from pathlib import Path

import pytest
from coverage_inputs import restore
from coverage_protocol import CoveragePlan, CoverageReview, validate_evidence
from inspect_artifacts import csv_profile, digest, hdf5_profile, main
from pydantic import ValidationError
from run_coverage import check_config


def test_csv_records_missing_nonfinite_duplicate_and_ragged_values(tmp_path):
    path = tmp_path / "observations.csv"
    path.write_text("id,value\na,1\na,NaN\nb,inf\nc,\nd,2,extra\ne,-3\n")
    result = csv_profile(path, distinct_limit=2)
    assert result["row_count"] == 6 and result["ragged_rows"] == 1
    names, values = result["columns"]
    assert names["distinct_capped"] and names["distinct_nonempty"] == 2
    assert values["empty"] == 1 and values["nonfinite_numeric"] == 2
    assert values["minimum"] == -3 and values["maximum"] == 1
    assert values["finite_numeric"] == 2


def test_csv_fingerprints_detect_order_and_row_limit_is_explicit(tmp_path):
    one = tmp_path / "one.csv"
    two = tmp_path / "two.csv"
    one.write_text("id\na\nb\n")
    two.write_text("id\nb\na\n")
    assert (
        csv_profile(one)["columns"][0]["ordered_values_sha256"]
        != csv_profile(two)["columns"][0]["ordered_values_sha256"]
    )
    with pytest.raises(ValueError, match="row inspection limit"):
        csv_profile(one, row_limit=1)


def test_hdf5_shapes_only_and_external_links_are_not_followed(tmp_path):
    import h5py

    path = tmp_path / "fixture.h5"
    with h5py.File(path, "w") as handle:
        handle.create_dataset("matrix", shape=(10000, 10000), dtype="f4", chunks=(10, 10))
        handle.create_dataset("labels", data=[1, 2, 3])
        handle["missing"] = h5py.ExternalLink("/not/a/real/file", "/secret")
        handle["alias"] = h5py.SoftLink("/labels")
    before = digest(path)
    result = hdf5_profile(path)
    nodes = {item["path"]: item for item in result["nodes"]}
    assert nodes["/matrix"]["shape"] == (10000, 10000)
    assert "preview" not in nodes["/matrix"]
    assert nodes["/labels"]["preview"] == [1, 2, 3]
    assert len(result["skipped_links"]) == 2
    assert digest(path) == before
    with pytest.raises(ValueError, match="node inspection limit"):
        hdf5_profile(path, node_limit=1)


def test_inspection_refuses_mismatched_identity_and_preserves_originals(tmp_path):
    inputs = tmp_path / "inputs"
    inputs.mkdir()
    data = inputs / "table.csv"
    data.write_text("id,value\na,1\n")
    manifest = tmp_path / "manifest.json"
    item = dict(path="table.csv", bytes=data.stat().st_size, sha256=digest(data))
    manifest.write_text(json.dumps(dict(artifacts=[item])))
    main(manifest, inputs, tmp_path / "profiles")
    assert digest(data) == item["sha256"]
    data.write_text("id,value\na,2\n")
    with pytest.raises(ValueError, match="identity mismatch"):
        main(manifest, inputs, tmp_path / "changed")


@pytest.mark.parametrize("path", ["../escape", "/absolute", "a/../b", "a//b"])
def test_archive_rejects_unsafe_paths(tmp_path, path):
    with pytest.raises(ValueError, match="relative"):
        restore(
            [dict(path=path, bytes=1, sha256="x")],
            prefix="memory",
            root=tmp_path,
            open_source=lambda _: io.BytesIO(b"x"),
            byte_limit=1,
        )


def test_archive_checks_size_and_hash_before_profile(tmp_path):
    item = dict(path="data.csv", bytes=2, sha256=hashlib.sha256(b"ok").hexdigest())
    receipts = restore(
        [item],
        prefix="memory",
        root=tmp_path / "good",
        open_source=lambda _: io.BytesIO(b"ok"),
        byte_limit=2,
    )
    assert receipts == [item]
    for label, contents in [("larger", b"bad"), ("wrong-hash", b"no")]:
        with pytest.raises(ValueError):
            restore(
                [item],
                prefix="memory",
                root=tmp_path / label,
                open_source=lambda _, data=contents: io.BytesIO(data),
                byte_limit=2,
            )
    with pytest.raises(ValueError, match="ceiling"):
        restore([item], prefix="memory", root=tmp_path / "cap", open_source=None, byte_limit=1)


def proposal():
    return dict(
        disposition="propose_contract",
        rationale="fixture",
        endpoints=[
            dict(
                name="result",
                scientific_result="result",
                source_evidence="source line",
                reference_evidence=[
                    dict(
                        artifact="table.csv",
                        location="value",
                        observation="column exists",
                        status="observed",
                    )
                ],
                proposed_representation="table",
                comparison_risks=["calibration pending"],
                required_executable_validation=["independent conforming result"],
            )
        ],
        supporting_artifacts=[],
        excluded_results_with_reasons=[],
        corrections_to_prior_claims=[],
        missing_reference_evidence=[],
        next_validation=[],
    )


def test_coverage_cannot_use_unobserved_artifacts_or_approve_missing_evidence():
    value = CoveragePlan.model_validate(proposal())
    with pytest.raises(ValueError, match="absent"):
        validate_evidence(value, [])
    with pytest.raises(ValueError, match="location is absent"):
        validate_evidence(value, [dict(path="table.csv")])
    assert (
        validate_evidence(value, [dict(path="table.csv", columns=[dict(name="value", position=1)])])
        is value
    )
    with pytest.raises(ValidationError, match="no known missing"):
        CoveragePlan.model_validate(
            {**proposal(), "missing_reference_evidence": ["missing branch"]}
        )
    with pytest.raises(ValidationError, match="empty defect lists"):
        CoverageReview(
            decision="approve",
            rationale="fixture",
            omitted_scientific_endpoints=[],
            unsupported_evidence_claims=["unknown column"],
            scientific_scope_changes=[],
            remaining_validation=[],
        )


def test_new_requests_account_for_prior_pipeline_work():
    config = json.loads(Path(__file__).with_name("coverage-inputs.json").read_text())
    check_config(config, dict(raw_model_requests=7))
    with pytest.raises(ValueError, match="allowance"):
        check_config(config, dict(raw_model_requests=72))


def test_coverage_launch_requires_private_archive_before_submission(tmp_path):
    from launch_iris import submit_prepared

    with pytest.raises(ValueError, match="recorded private reference archive"):
        submit_prepared(
            None,
            files={"campaign-config.json": json.dumps({"entrypoint": "run_coverage.py"}).encode()},
            revision="fixture",
            receipt=tmp_path / "receipt.json",
            token="fixture",
            daytona_key="fixture",
            artifact_prefix="s3://fixture",
            endpoint_job="fixture",
            cluster="fixture",
        )
    assert not (tmp_path / "receipt.json").exists()
