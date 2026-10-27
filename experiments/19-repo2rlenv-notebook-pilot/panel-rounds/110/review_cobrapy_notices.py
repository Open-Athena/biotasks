"""Record this release's reviewed notices outside its unchanged scientific task."""

import gzip
import hashlib
import html
import json
import re
from datetime import UTC, datetime
from pathlib import Path

PRIVATE = Path("/home/exedev/.local/share/biotasks/handoffs/issue-19")
PUBLIC = Path(__file__).resolve().parents[2] / "autonomous-runs/226"
SOURCES = PRIVATE / "publication-review226"
TASK = PRIVATE / "archives/226/snapshot-restored/files/native/tasks/autonomous-panel-226"


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def read(path):
    return json.loads(path.read_text())


def save(name, value):
    target = PUBLIC / name
    assert not target.exists()
    target.write_text(json.dumps(value, indent=2) + "\n")


def main():
    sources = read(SOURCES / "primary-readback.json")
    package = read(SOURCES / "immutable-package-source.json")
    assert package["package_and_notebook_license_identical"] is True
    notebook = (SOURCES / "notebook-LICENSE.txt").read_bytes()
    assert sha(notebook) == package["package_license_sha256"]
    compressed = (SOURCES / "textbook.xml.gz").read_bytes()
    model = (TASK / "environment/inputs/e_coli_core.xml").read_bytes()
    assert gzip.decompress(compressed) == model
    assert sha(model) == sources["input_sha256"]
    recorded = (TASK / "environment/SOURCE-LICENSES.json").read_bytes()
    bundled = json.loads(recorded)
    source = bundled["notebook"]
    assert source["source_sha256"] == (
        "64da8bc313b923ae2e536964cb0db903e94d9eefa6ee7c8b593ebe2000507115"
    )
    template_raw = (SOURCES / "bigg-about-license.html").read_bytes()
    section = re.split(
        r"<h4\b[^>]*>\s*License\s*</h4>", template_raw.decode(), maxsplit=1, flags=re.I
    )[1]
    paragraphs = [
        " ".join(html.unescape(re.sub("<[^>]+>", " ", value)).split())
        for value in re.findall(r"<p>(.*?)</p>", section, flags=re.S)
    ]
    assert len(paragraphs) == 6
    assert paragraphs[0] == "Copyright © 2019 The Regents of the University of California"
    assert "educational, research and non-profit purposes" in paragraphs[2]
    assert "commercial purposes" in paragraphs[3]
    bigg_text = "\n\n".join(paragraphs) + "\n"
    notices = {
        "scope": "Publication documents accompanying the exact unchanged tested task; not a blanket relicense.",
        "notebook_and_package": {
            "source_url": package["package_license_url"],
            "notebook_source_url": source["provenance"]["notebook"]["license_url"],
            "original_text_sha256": sha(notebook),
            "original_text": notebook.decode(),
        },
        "model_data": {
            "source_url": "https://bigg.ucsd.edu/license",
            "pinned_template_sha256": sha(template_raw),
            "full_notice_text": bigg_text,
            "notice_text_sha256": sha(bigg_text.encode()),
            "scope": "Educational, research and nonprofit use/redistribution under the complete retained notice; no commercial permission is granted by this release.",
        },
        "notice_template_server_code": {
            "original_text": (SOURCES / "bigg-server-LICENSE.txt").read_text(),
            "original_text_sha256": sha((SOURCES / "bigg-server-LICENSE.txt").read_bytes()),
        },
        "task_science_or_native_bundle_edited": False,
    }
    primary = []
    for record in sources["primary_sources"]:
        item = {key: value for key, value in record.items() if key != "saved_private"}
        if item["path"] == "src/cobra/data/textbook.xml.gz":
            item.update(revision=package["commit"], url=package["immutable_model_url"])
        primary.append(item)
    review = {
        "observed_at": datetime.now(UTC).isoformat(),
        "campaign": 226,
        "scope": "Source-specific operator publication review for a public research release, with component notices; no scientific edit or new execution.",
        "source_revision": source["source_revision"],
        "notebook_source_sha256": source["source_sha256"],
        "source_notices_sha256": sha(recorded),
        "primary_sources": primary,
        "inputs": [
            {
                "path": "e_coli_core.xml",
                "sha256": sha(model),
                "bytes": len(model),
                "source_url": package["immutable_model_url"],
                "compressed_parent_sha256": sha(compressed),
                "compressed_parent_git_blob_sha1": package["model_git_blob_sha1"],
                "exact_uncompressed_parent_match": True,
                "terms": "Research/nonprofit redistribution with the full BiGG copyright, permission, commercial-use and disclaimer paragraphs preserved. The original package/notebook license text is retained separately; this release does not grant unrestricted commercial or commercial-training rights.",
            }
        ],
        "publication_scope": "Public research release under retained component terms, not unrestricted reuse",
        "public_research_release_eligible": True,
        "commercial_reuse_permission_granted": False,
        "original_notice_texts_and_copyright_retained": True,
        "historical_pending_review_flag_preserved": True,
        "historical_pending_review_superseded_for_these_exact_bytes": True,
        "data_origin": "Curated E. coli core metabolic reconstruction bundled with COBRApy; not observed flux measurements.",
        "limitations": [
            "The exact task supplies only e_coli_core; the original notebook also executes iJO1366 as a timing diagnostic, but that model is not a released task input.",
            "This review applies only to these exact bytes and this research release. It does not establish scientific validity, unrestricted third-party rights or commercial reuse permission.",
        ],
        "task_science_or_native_bundle_edited": False,
    }
    PUBLIC.mkdir(parents=True, exist_ok=True)
    save("publication-notices.json", notices)
    save("input-notice-review.json", review)
    save(
        "fresh-primary-notices.json",
        {
            "observed_at": review["observed_at"],
            "primary_sources": primary,
            "immutable_package_commit": package["commit"],
            "package_and_notebook_license_identical": True,
            "exact_final_input_matches_decompressed_package_file": True,
            "input_sha256": sha(model),
            "input_bytes": len(model),
        },
    )
    print(
        json.dumps(
            {
                "campaign": 226,
                "input_exact_source_match": True,
                "public_research_release_eligible": True,
                "commercial_permission_granted": False,
                "task_edited": False,
            }
        )
    )


if __name__ == "__main__":
    main()
