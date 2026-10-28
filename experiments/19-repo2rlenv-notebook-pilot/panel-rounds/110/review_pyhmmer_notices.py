"""Record source-specific notices for unchanged PyHMMER 227 release inputs.

Publication metadata only. This program never supplies a scientific worker with
task content, changes a task, creates resources or decides scientific validity.
"""

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

BASE = Path("/home/exedev/.local/share/biotasks/handoffs/issue-19")
PUBLIC = Path(__file__).resolve().parents[2] / "autonomous-runs/227"
PRIMARY = BASE / "publication-review227/primary-20261028"
TASK = BASE / "archives/227/snapshot-restored/files/native/tasks/autonomous-panel-227"


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def main():
    recorded = (TASK / "environment/SOURCE-LICENSES.json").read_bytes()
    original = Path(__file__).resolve().parents[2] / (
        "autonomous-cases/pyhmmer-msa-to-hmm/source-license-evidence.json"
    )
    assert original.read_bytes() == recorded
    notices = json.loads(recorded)
    primary = json.loads((PRIMARY / "readback.json").read_text())
    assert primary["original_reviewed_input_hashes_and_bytes_match_primary"] is True
    assert primary["original_mit_notice_matches_primary"] is True
    by_id = {row["id"]: row for row in primary["records"]}
    license_raw = (PRIMARY / "pyhmmer-copying.txt").read_bytes()
    assert sha(license_raw) == notices["notebook_license"]["sha256"]
    assert license_raw.decode() == notices["notebook_license"]["text"]
    expected = {}
    for index, row in enumerate(notices["reviewed_inputs"]):
        retrieved = by_id[f"input-{index}"]
        assert retrieved["status"] == 200
        raw = (PRIMARY / f"input-{index}.txt").read_bytes()
        assert sha(raw) == row["sha256"] == retrieved["sha256"]
        assert len(raw) == row["bytes"] == retrieved["bytes"]
        expected[sha(raw), len(raw)] = row
    assert len(expected) == len(notices["reviewed_inputs"]) == 2
    inputs = []
    for path in sorted((TASK / "environment/inputs").rglob("*")):
        assert not path.is_symlink()
        if not path.is_file():
            continue
        raw = path.read_bytes()
        row = expected.pop((sha(raw), len(raw)))
        inputs.append(
            {
                **row,
                "path": path.relative_to(TASK / "environment/inputs").as_posix(),
                "exact_original_primary_source_match": True,
            }
        )
    assert not expected
    sources = [row for row in primary["records"] if row["status"] == 200]
    sources.append(
        {
            "id": "pfam-license-web-readback",
            "url": "https://pfam-docs.readthedocs.io/en/dev/#license",
            "observed_date": "2026-10-28",
            "method": "Official documentation read through web.open",
            "finding": "Pfam is available under CC0.",
            "direct_download_status": 403,
            "raw_download_verified": False,
        }
    )
    review = {
        "observed_at": datetime.now(UTC).isoformat(),
        "campaign": 227,
        "scope": "Operator source-specific publication review of the exact unchanged tested task inputs.",
        "notebook_source_sha256": notices["notebook_source_sha256"],
        "source_notices_sha256": sha(recorded),
        "primary_sources": sources,
        "inputs": inputs,
        "public_research_release_eligible": True,
        "original_notice_texts_and_copyright_retained": True,
        "data_origin": "Curated Pfam LuxC alignment and UniProt protein sequences from the pinned PyHMMER repository; no simulated or operator-substituted data.",
        "limitations": [
            "Component MIT, Pfam CC0 and UniProt CC BY4.0 notices apply separately; this is not a blanket relicense or a grant of other third-party rights.",
            "Pfam's official documentation was available to the web reader; the direct HTTP403 is preserved without claiming a byte-verified download.",
            "Scientific/native acceptance and anonymous release download remain separate gates.",
        ],
        "task_science_or_native_bundle_edited": False,
    }
    documents = {
        "scope": "Notices accompanying the exact unchanged released inputs and notebook.",
        "notebook": {
            "source_url": notices["notebook_license"]["source_url"],
            "original_text_sha256": sha(license_raw),
            "original_text": license_raw.decode(),
        },
        "data_sources": notices["data_license"]["sources"],
        "uniprot_official_license_response": json.loads(
            (PRIMARY / "uniprot-license.txt").read_text()
        ),
        "attribution": "PyHMMER: Martin Larralde; Pfam PF05893.5 LuxC alignment; The UniProt Consortium protein sequences. Preserve the original Stockholm and FASTA accession headers and source links.",
        "task_science_or_native_bundle_edited": False,
    }
    PUBLIC.mkdir(parents=True, exist_ok=True)
    for name, value in {
        "input-notice-review.json": review,
        "publication-notices.json": documents,
        "fresh-primary-notices.json": primary,
    }.items():
        path = PUBLIC / name
        assert not path.exists()
        path.write_text(json.dumps(value, indent=2) + "\n")
    print(
        json.dumps(
            {
                "campaign": 227,
                "exact_reviewed_inputs": len(inputs),
                "public_research_release_eligible": True,
                "task_edited": False,
            }
        )
    )


if __name__ == "__main__":
    main()
