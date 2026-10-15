"""Render the saved worker plan as Markdown without rewriting its content."""

import json
import sys
from pathlib import Path


def render(directory):
    plan = json.loads((directory / "plan.json").read_text())
    parts = [
        "# Preparation worker output",
        "Rendered from [plan.json](plan.json). Generated commands and source edits have not "
        "been executed. Only structural checks have run; scientific fidelity is unreviewed.",
    ]
    inspection = directory / "inspection.json"
    if inspection.exists():
        record = json.loads(inspection.read_text())
        if record.get("ready_for_execution") is False:
            parts.append("**Not ready for execution.** " + record["review_kind"] + ".")
            parts.append("\n".join("- " + finding for finding in record["findings"]))
            parts.append("The worker's output below is preserved unchanged; these findings are separate annotations.")

    def field(title, value):
        parts.extend(["## " + title, value])

    def code(value, language):
        fence = "`" * max(3, max((len(x) for x in value.split() if set(x) == {"`"}), default=0) + 1)
        return fence + language + "\n" + value + "\n" + fence

    field("Decision", plan["disposition"] + "\n\n" + plan["explanation"])
    if "environment_rationale" in plan:
        field("Environment rationale", plan["environment_rationale"])
    if "pyproject_toml" in plan:
        field("Python dependencies", code(plan["pyproject_toml"], "toml"))
        field("System packages", code(json.dumps(plan["system_packages"], indent=2), "json"))
        field("Input staging script", code(plan["stage_inputs_sh"], "sh"))
        field("Controller setup script", code((directory / "setup.sh").read_text(), "sh") if (directory / "setup.sh").exists() else "Not materialized.")
    elif "setup_sh" in plan:
        field("Setup script", code(plan["setup_sh"], "sh"))
    for index, branch in enumerate(plan.get("branches", []), 1):
        field(f"Scientific branch {index}: {branch['name']}", branch["scientific_result"])
        parts.extend(["Source evidence: " + branch["source_evidence"],
                      "Artifacts: " + ", ".join(f"`{path}`" for path in branch["artifacts"])])
    for artifact in plan["artifacts"]:
        field("Artifact: " + artifact["path"], artifact["description"])
        parts.append("Source evidence: " + artifact["source_evidence"])
    if "export_code" in plan:
        field("Worker-returned export code", code(plan["export_code"], "python"))
        if (directory / "reference.py").exists():
            field("Controller-assembled reference script", "[reference.py](reference.py): untouched original script followed by the export code above.")
        if (directory / "source.diff").exists():
            field("Controller-computed diff", code((directory / "source.diff").read_text(), "diff"))
    elif "reference_script" in plan:
        field("Complete edited script", code(plan["reference_script"], "python"))
        if (directory / "source.diff").exists():
            field("Controller-computed diff", code((directory / "source.diff").read_text(), "diff"))
    else:
        for index, change in enumerate(plan["changes"], 1):
            field(f"Source edit {index}: {change['purpose']}", change["justification"])
            parts.extend(["**Before**", code(change["before"], "python"),
                          "**After**", code(change["after"], "python")])
    for title, key in [("Excluded outputs", "excluded_outputs"),
                       ("Unresolved assumptions", "unresolved_assumptions")]:
        field(title, "\n\n".join("- " + item for item in plan[key]) or "None listed.")
    (directory / "plan.md").write_text("\n\n".join(parts) + "\n")


if __name__ == "__main__":
    render(Path(sys.argv[1]))
