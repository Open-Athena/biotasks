"""Summarize original source identities and audited states, never run a task."""

import argparse
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument(
    "launch_root", type=Path, help="Private original payload/typed-observation directory"
)
args = parser.parse_args()
root = Path(__file__).resolve().parent
experiment = root.parents[1]
selection = [
    ("cobrapy-deletions", "Constraint-based metabolism", 133),
    ("pyhmmer-msa-to-hmm", "Protein sequence profiles", 134),
    ("matchms-spectral-matching", "Metabolite mass spectra", 144),
    ("neurokit-hrv", "Physiological signal analysis", 136),
    ("scanpy-clustering", "Single-cell transcriptomics", 137),
    ("bioframe-motifs-to-peaks", "Genomic intervals", 138),
    ("pyteomics-filtering", "Proteomic search results", 139),
    ("mdanalysis-rmsd", "Molecular dynamics", 140),
    ("sgkit-relatedness", "Statistical genetics", 142),
    ("pymc-rat-tumor", "Bayesian biological inference", 143),
]
records, live = [], []
for identifier, domain, number in selection:
    payload = args.launch_root / f"{number:03}-payload"
    manifest = json.loads((payload / "inputs.json").read_text())
    raw = (payload / "seeds.json").read_bytes()
    assert hashlib.sha256(raw).hexdigest() == manifest["files"]["seeds.json"]
    seed = json.loads(raw)[0]
    row = {
        "id": identifier,
        "original_seed_id": seed.get("id"),
        "domain": domain,
        "latest_campaign": number,
        "source_url": seed["url"],
        "source_sha256": seed["source_sha256"],
        "source_revision": seed["source_revision"],
        "notebook_license": seed.get("license"),
        "language": "Python",
        "data_lineage": seed.get("provenance", {}).get("data_lineage"),
    }
    results = list(experiment.glob(f"panel-rounds/*/result-{number}.json"))
    assert len(results) <= 1
    result = results[0] if results else None
    if result is not None:
        data = json.loads(result.read_text())
        assert data["original_and_fresh_cleanup_verified"]
        row.update(
            state=data["audited_state"],
            terminal_original_audited=True,
            native_controls_passed=bool(data.get("native_rewards")),
            fully_qualified_task=data.get("fully_qualified_task", False),
            published=data.get("published", False),
            evidence=str(result.relative_to(experiment)),
            evidence_sha256=hashlib.sha256(result.read_bytes()).hexdigest(),
            factory_revision=data["frozen_worker_revision"],
            operator_scientific_edits=data["operator_scientific_edits"],
        )
    elif (args.launch_root / f"{number:03}-submission.json").exists():
        claim = args.launch_root / f"{number:03}-submission.json"
        observed = max(
            (args.launch_root / "typed-observations").glob(f"{number:03}-*.json"),
            key=lambda path: path.stat().st_mtime,
        )
        data = json.loads(observed.read_text())
        assert data["state"] == "RUNNING" or data["terminal"] is True
        assert data["claim_sha256"] == hashlib.sha256(claim.read_bytes()).hexdigest()
        freezes = list(experiment.glob(f"panel-rounds/*/freeze-{number}.json"))
        assert len(freezes) == 1
        freeze = json.loads(freezes[0].read_text())
        live.append(data)
        row.update(
            state="terminal_awaiting_original_audit" if data["terminal"] else "running",
            terminal_original_audited=False,
            native_controls_passed=None,
            fully_qualified_task=None,
            published=False,
            evidence="panel-rounds/028/live-jobs.json",
            factory_revision=freeze["public_runtime_revision"],
            operator_scientific_edits=0,
        )
    else:
        assert number == 143 and not (args.launch_root / "143-submission.json").exists()
        freeze = json.loads((root / "freeze-143.json").read_text())
        row.update(
            state="frozen_queued_not_submitted",
            terminal_original_audited=False,
            native_controls_passed=None,
            fully_qualified_task=None,
            published=False,
            evidence="panel-rounds/028/freeze-143.json",
            factory_revision=freeze["public_runtime_revision"],
            operator_scientific_edits=0,
        )
    records.append(row)
assert len(records) == len({row["id"] for row in records}) == 10
assert len({row["source_url"] for row in records}) == 10
assert len({row["source_sha256"] for row in records}) == 10
(root / "live-jobs.json").write_text(
    json.dumps(
        {
            "observations": live,
            "scope": "Typed job status only; not scientific completion or release.",
        },
        indent=2,
    )
    + "\n"
)
counts = {
    "selected_python_domains": len(records),
    "terminal_original_audits": sum(row["terminal_original_audited"] for row in records),
    "native_control_passes": sum(row["native_controls_passed"] is True for row in records),
    "unsupported_conversion_profile": sum(
        row["state"] == "unsupported_conversion_profile" for row in records
    ),
    "running": sum(row["state"] == "running" for row in records),
    "terminal_awaiting_original_audit": sum(
        row["state"] == "terminal_awaiting_original_audit" for row in records
    ),
    "queued_not_submitted": sum(row["state"] == "frozen_queued_not_submitted" for row in records),
    "fully_qualified_latest_tasks": sum(row["fully_qualified_task"] is True for row in records),
}
report = {
    "observed_at": datetime.now(UTC).isoformat(),
    "scope": "Current ten-domain Python development panel across recorded factory versions. Not one frozen-version holdout or a success-rate estimate.",
    "counts": counts,
    "records": records,
    "excluded_from_this_ten_source_panel": [
        {"id": "pyradiomics-brain", "campaign": 141, "reason": "Unsubmitted execution/access hold."}
    ],
    "prior_published_example": {
        "id": "pyhmmer-msa-to-hmm",
        "campaign": 124,
        "note": "Earlier public case, distinct from latest rejected134; not substituted for that outcome.",
    },
}
(root / "development-panel.json").write_text(json.dumps(report, indent=2) + "\n")
text = (
    "# Current ten-domain Python development panel\n\n"
    "This is a development panel across recorded factory versions, not a single-version holdout. "
    "The latest case per source is shown; native controls are separate from full task qualification and release.\n\n"
    "| Domain | Original notebook | Latest campaign | Current evidence |\n"
    "| --- | --- | --- | --- |\n"
)
for row in records:
    text += (
        f"| {row['domain']} | [{row['id']}]({row['source_url']}) | {row['latest_campaign']} | "
        f"[{row['state'].replace('_', ' ')}](../../{row['evidence']}) |\n"
    )
text += (
    f"\n{counts['terminal_original_audits']} latest cases have terminal original-evidence audits, "
    f"running: {counts['running']}; frozen but unsubmitted: {counts['queued_not_submitted']}. "
    f"{counts['native_control_passes']} passed native controls; qualification holds remain. "
    "Five terminal cases reject generated setup/tasks; one stops at unsupported notebook conversion. "
    "These are not demonstrated broken source notebooks. "
    "Earlier Matchms135 infrastructure failure is preserved;144 is a fresh run. "
    "Earlier PyHMMER124 remains the latest qualified public release and is not substituted for134 here.\n\n"
    "PyRadiomics141 remains on its execution/access hold and is not counted as a tested tenth notebook. "
    "PyMC143 is the selected tenth domain; original source and all branches remain intact, with suitability left to the factory. "
    "R support stays deferred.\n"
)
(root / "development-panel.md").write_text(text)
assert all((experiment / row["evidence"]).is_file() for row in records)
print(json.dumps(counts))
