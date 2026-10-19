"""Publication must use the selected source and the bundle's actual attribution."""

import hashlib
import json

import pytest
from release_metadata import load_release_metadata, verify_bundle_licenses


def configuration(tmp_path):
    license_text = "Fixture source license\n"
    licenses = {
        "notebook_license": {
            "text": license_text,
            "sha256": hashlib.sha256(license_text.encode()).hexdigest(),
        }
    }
    license_file = tmp_path / "licenses.json"
    license_file.write_text(json.dumps(licenses))
    seed_file = tmp_path / "seed.json"
    provenance = {"notebook": {"url": "https://example.org/selected-source"}}
    seed_file.write_text(json.dumps([{"provenance": provenance}]))
    metadata = dict(
        repo_id="owner/new-release",
        title="Selected task",
        description="Fixture",
        methodology="Measured controls",
        licenses_file=str(license_file),
        seed_file=str(seed_file),
        citations=[provenance["notebook"]["url"]],
    )
    return {"release_metadata": metadata}, licenses, provenance


def test_release_uses_explicit_source(tmp_path):
    config, licenses, provenance = configuration(tmp_path)
    metadata, loaded, source = load_release_metadata(config)
    assert metadata == config["release_metadata"]
    assert loaded == licenses and source == provenance
    environment = tmp_path / "task/environment"
    environment.mkdir(parents=True)
    (environment / "SOURCE-LICENSES.json").write_text(json.dumps(licenses))
    verify_bundle_licenses(environment.parent, licenses)
    with pytest.raises(ValueError, match="validated task bundle"):
        verify_bundle_licenses(environment.parent, {"other_source": "wrong attribution"})


def test_missing_metadata_never_falls_back_to_previous_task():
    with pytest.raises(ValueError, match="release_metadata"):
        load_release_metadata({})


def test_ambiguous_seed_and_changed_license_rejected(tmp_path):
    config, licenses, provenance = configuration(tmp_path)
    seed_file = tmp_path / "seed.json"
    seed_file.write_text(json.dumps([{"provenance": provenance}] * 2))
    with pytest.raises(ValueError, match="single explicitly selected"):
        load_release_metadata(config)
    seed_file.write_text(json.dumps([{"provenance": provenance}]))
    licenses["notebook_license"]["text"] = "changed"
    (tmp_path / "licenses.json").write_text(json.dumps(licenses))
    with pytest.raises(ValueError, match="recorded hash"):
        load_release_metadata(config)


def test_cross_wired_source_provenance_rejected(tmp_path):
    config, licenses, _ = configuration(tmp_path)
    licenses["source_provenance"] = {"notebook": {"url": "https://example.org/other-source"}}
    (tmp_path / "licenses.json").write_text(json.dumps(licenses))
    with pytest.raises(ValueError, match="bundled source provenance"):
        load_release_metadata(config)
