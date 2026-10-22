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


def attribution_fixture(tmp_path):
    source = {"source_sha256": "a" * 64, "provenance": {"notebook": "pinned source"}}
    text = "Original source license\n"
    notices = {
        "source_provenance": source["provenance"],
        "notebook_source_sha256": source["source_sha256"],
        "notebook_license": {"text": text, "sha256": hashlib.sha256(text.encode()).hexdigest()},
        "reviewed_inputs": [
            {
                "sha256": "b" * 64,
                "bytes": 123,
                "source_url": "https://example.org/data",
                "terms": "Fixture reviewed terms",
            },
        ],
    }
    (tmp_path / "notices.json").write_text(json.dumps(notices))
    materialization = tmp_path / "materialized"
    materialization.mkdir()
    (materialization / "manifest.json").write_text(
        json.dumps({"inputs": [{"path": "renamed/input.dat", "sha256": "b" * 64, "bytes": 123}]})
    )
    return {"source_notices_file": "notices.json"}, source, notices, materialization


def test_campaign_notices_are_preserved_before_native_packaging(tmp_path):
    from release_metadata import campaign_attribution

    config, seed, notices, materialized = attribution_fixture(tmp_path)
    assert campaign_attribution(config, seed, materialized, experiment_root=tmp_path) == notices
    environment = tmp_path / "task/environment"
    environment.mkdir(parents=True)
    (environment / "SOURCE-LICENSES.json").write_text(json.dumps(notices))
    verify_bundle_licenses(environment.parent, notices)
    assert json.loads((tmp_path / "notices.json").read_text()) == notices


def test_unreviewed_campaign_remains_explicitly_local(tmp_path):
    from release_metadata import campaign_attribution

    seed = {"id": "new source"}
    assert campaign_attribution({}, seed, tmp_path / "missing", experiment_root=tmp_path) == {
        "notebook": seed,
        "publication_status": "Not assessed; local validated task only",
    }


@pytest.mark.parametrize(
    "defect", ["source", "identity", "license", "input", "bytes", "terms", "empty"]
)
def test_campaign_notices_cannot_cover_another_source_or_unreviewed_input(tmp_path, defect):
    from release_metadata import campaign_attribution

    config, seed, notices, materialized = attribution_fixture(tmp_path)
    if defect == "source":
        notices["source_provenance"] = {"notebook": "another source"}
    elif defect == "identity":
        notices["notebook_source_sha256"] = "c" * 64
    elif defect == "license":
        notices["notebook_license"]["text"] = "changed text"
    elif defect == "input":
        notices["reviewed_inputs"][0]["sha256"] = "c" * 64
    elif defect == "bytes":
        notices["reviewed_inputs"][0]["bytes"] = 122
    elif defect == "terms":
        notices["reviewed_inputs"][0]["terms"] = ""
    else:
        notices["reviewed_inputs"] = []
    (tmp_path / "notices.json").write_text(json.dumps(notices))
    with pytest.raises(ValueError):
        campaign_attribution(config, seed, materialized, experiment_root=tmp_path)


@pytest.mark.parametrize("bad", ["../notices.json", "/notices.json", "case//notices.json", ".", 42])
def test_campaign_notice_path_is_explicit_and_relative(tmp_path, bad):
    from release_metadata import campaign_attribution

    with pytest.raises(ValueError, match="canonical"):
        campaign_attribution({"source_notices_file": bad}, {}, tmp_path, experiment_root=tmp_path)


def test_campaign_notices_cannot_read_a_symlink(tmp_path):
    from release_metadata import campaign_attribution

    config, seed, _, materialized = attribution_fixture(tmp_path)
    (tmp_path / "linked.json").symlink_to(tmp_path / "notices.json")
    config["source_notices_file"] = "linked.json"
    with pytest.raises(ValueError, match="regular file"):
        campaign_attribution(config, seed, materialized, experiment_root=tmp_path)


def test_campaign_notices_cannot_follow_a_parent_directory_outside_experiment(tmp_path):
    from release_metadata import campaign_attribution

    config, seed, _, materialized = attribution_fixture(tmp_path)
    experiment = tmp_path / "experiment"
    experiment.mkdir()
    (experiment / "outside").symlink_to(tmp_path, target_is_directory=True)
    config["source_notices_file"] = "outside/notices.json"
    with pytest.raises(ValueError, match="regular file"):
        campaign_attribution(config, seed, materialized, experiment_root=experiment)
