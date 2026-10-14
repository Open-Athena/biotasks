"""Build a standalone explanatory map, embedding canonical prompt files verbatim."""

import hashlib
import html
import json
import re
import subprocess
from pathlib import Path

from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import BashLexer, DiffLexer, JsonLexer, MarkdownLexer, PythonLexer, TextLexer

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
REVISION = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
BASE = f"https://github.com/Open-Athena/biotasks/blob/{REVISION}/"
EXP = "experiments/19-repo2rlenv-notebook-pilot/"


def row(name, value):
    return {"name": name, "value": value}


SOURCE = row(
    "Original notebook",
    "Notebook Markdown and code cells rendered as text, plus title, URL, revision, hash, license and input-data provenance. The rendered seed does not include saved cell outputs.",
)
BASELINE = row(
    "Untouched script",
    "The deterministically converted Python script, before input-path or export changes.",
)
PROFILES = row(
    "Observed file profiles",
    "Each file’s path, size and SHA-256. CSV/TSV: headers, row counts, missing/nonfinite counts, numeric ranges, bounded distinct counts, column hashes and examples. HDF5: paths, encodings, shapes, types and bounded previews. These are summaries, not the full biological matrices.",
)
CONTEXT = [
    SOURCE,
    BASELINE,
    row(
        "Executed script + diff",
        "The complete reference script that ran successfully, and its exact changes relative to the untouched script.",
    ),
    PROFILES,
    row(
        "Earlier preparation plan",
        "GLM’s proposed exports and branch mapping, exclusions, source edits, dependency/setup shell script, environment rationale and unresolved assumptions. These are prior model claims, not measurements.",
    ),
    row(
        "Earlier preparation review",
        "The earlier GLM review’s decision, rationale, defect lists and checks recommended for execution.",
    ),
    row(
        "Execution record + run summary",
        "Command, exit status, elapsed time and memory measurement. Also the full reference summary: repair history, input preservation, archive/cleanup checks and model-request usage. Some of this operational detail may be unnecessary for endpoint selection; it is currently included.",
    ),
]

STAGES = [
    dict(
        id="convert",
        number="01",
        title="Convert source",
        kind="code",
        group="Reference",
        purpose="Make the notebook’s code available as a plain script while retaining its narrative separately.",
        inputs=[row("Pinned notebook", "The selected source notebook and its recorded identity.")],
        outputs=[
            "Untouched baseline.py and conversion.json with source/script hashes.",
            "A seed containing the notebook’s Markdown and code as text plus provenance.",
        ],
        note="The implemented pilot is Python. This diagram does not claim support for every notebook language.",
        files=["reference-inputs/scanpy/conversion.json"],
    ),
    dict(
        id="prepare",
        number="02",
        title="Prepare reference",
        kind="llm",
        group="Reference",
        purpose="Propose dependencies, faithful input staging and exports of the notebook’s scientific results.",
        inputs=[
            SOURCE,
            BASELINE,
            row("Conversion record", "Source/script identities and conversion metadata."),
            row(
                "Staged original inputs",
                "Recorded identities and locations of the downloaded original input files.",
            ),
            row(
                "Execution limits",
                "The reference configuration, including resources and remaining setup time.",
            ),
            row(
                "Previous feedback, if any",
                "Earlier plans plus review defects or setup/execution failures. Empty on the first pass.",
            ),
        ],
        outputs=[
            "ReferencePlan: setup shell script, anchored source edits, artifact inventory and scientific-branch mapping.",
            "Exclusions, uncertainties, and a prepare/reject decision.",
        ],
        prompt="notebook-reference-prepare",
        schema="reference_protocol.py",
        fields=[
            "disposition",
            "explanation",
            "environment_rationale",
            "setup_sh",
            "changes",
            "artifacts",
            "branches",
            "excluded_outputs",
            "unresolved_assumptions",
        ],
        note="This worker already proposes which scientific results to export. It is not only installing packages. The export plan is checked again against actual files later.",
        files=["run_reference.py", "reference_protocol.py"],
    ),
    dict(
        id="reference-review",
        number="03",
        title="Review preparation",
        kind="llm",
        group="Reference",
        purpose="Check the proposed setup and exports against the original notebook before running them.",
        inputs=[
            row(
                "All preparation inputs",
                "The same original notebook, untouched script, conversion, staged input records, limits and previous feedback supplied to step 02.",
            ),
            row(
                "Proposed ReferencePlan",
                "The complete output of step 02, including setup commands and export changes.",
            ),
            row(
                "Materialized source diff",
                "The controller applies the proposed anchored edits and supplies their exact diff. It also checks the resulting script’s syntax before this review.",
            ),
        ],
        outputs=[
            "ReferenceReview: approve, revise or reject.",
            "Defect lists for omissions, scientific changes, setup/export problems; unresolved execution checks.",
        ],
        prompt="notebook-reference-review",
        schema="reference_protocol.py",
        fields=[
            "decision",
            "rationale",
            "omitted_scientific_results",
            "prohibited_scientific_changes",
            "setup_or_export_problems",
            "checks_for_execution",
        ],
        note="A static model review cannot establish that the script runs or that its results are scientifically correct. The existing reference controller can send defects back to step 02; the newly agreed one-repair sequence applies to endpoint creation below.",
        files=["run_reference.py", "reference_protocol.py"],
    ),
    dict(
        id="execute",
        number="04",
        title="Execute reference",
        kind="code",
        group="Reference",
        purpose="Run the reviewed script on the original inputs and preserve its real outputs.",
        inputs=[
            row("Reviewed setup script", "Commands generated in step 02 and approved in step 03."),
            row(
                "Reviewed reference script",
                "The baseline plus the permitted input-staging and export edits.",
            ),
            row("Original input files", "The biological data itself, staged into the sandbox."),
            row(
                "Resource and execution settings",
                "CPU-only Daytona sandbox, setup allowance, offline analysis and reference runtime limit.",
            ),
        ],
        outputs=[
            "Exported scientific files, dependency/input records and file hashes.",
            "Exit status, stdout/stderr, timing and memory observations; source script and diff.",
        ],
        note="Execution itself makes no LLM calls. Setup has internet; analysis runs offline. Failures can become feedback for reference preparation. A successful exit is not scientific validation.",
        files=["run_reference.py", "reference_remote.py"],
    ),
    dict(
        id="inspect",
        number="05",
        title="Inspect saved files",
        kind="code",
        group="Endpoints",
        purpose="Measure the structure of reference outputs without rerunning the analysis.",
        inputs=[
            row(
                "Archived reference outputs",
                "The actual files from step 04, retrieved into the inspection worker.",
            ),
            row(
                "Pinned inventories",
                "The original size/hash inventory and archive manifest, checked before reading.",
            ),
        ],
        outputs=[
            "Structural profiles for every supported CSV/TSV or HDF5 file.",
            "Retrieval receipts and before/after identity checks.",
        ],
        note="Streams tables; inspects HDF5 structure and small previews without loading full matrices. Unsupported formats and inspection limits are explicit. The next model receives these profiles, not direct file access.",
        files=["coverage_inputs.py", "inspect_artifacts.py"],
    ),
    dict(
        id="create",
        number="06",
        title="Create endpoint proposal",
        kind="llm",
        group="Endpoints",
        purpose="Decide which scientific results the single task should require, using the executed source and observed evidence.",
        inputs=CONTEXT,
        outputs=[
            "CoveragePlan: proposed scientific endpoints and compact solver-facing representations.",
            "Evidence citations, exclusions, corrected prior claims, missing reference evidence and validation needs.",
            "A propose-contract, reference-work-required or reject decision.",
        ],
        prompt="notebook-endpoint-coverage",
        schema="coverage_protocol.py",
        fields=[
            "disposition",
            "rationale",
            "endpoints",
            "supporting_artifacts",
            "excluded_results_with_reasons",
            "corrections_to_prior_claims",
            "missing_reference_evidence",
            "next_validation",
        ],
        note="This is an endpoint proposal, not task construction or a grading contract. The worker has submission/revision tools only: it cannot open files, browse or run analysis. The notebook and scripts overlap, and previous model opinions are currently included; these inputs are open for review.",
        files=["run_coverage.py", "coverage_protocol.py"],
    ),
    dict(
        id="check",
        number="07",
        title="Check submission",
        kind="code",
        group="Endpoints",
        purpose="Check the proposal’s structure and whether cited evidence locations exist.",
        inputs=[
            row("Submitted proposal", "The structured output from step 06 or its optional repair."),
            row(
                "Schema + observed profiles",
                "Required fields and types, consistency rules, known artifact paths, exact CSV headers and HDF5 paths.",
            ),
        ],
        outputs=["An accepted structured proposal, or concrete validation errors."],
        note="These checks can reject a nonexistent column or an inconsistent decision. They cannot detect every omitted scientific branch or prove that an evidence claim is true.",
        files=["coverage_protocol.py", "reference_stage.py"],
    ),
    dict(
        id="repair",
        number="08",
        title="Repair if rejected",
        kind="llm",
        group="Endpoints",
        purpose="Correct a creation submission that failed the programmatic checks, once.",
        inputs=[
            row(
                "Original creation context",
                "The same instructions, notebook, scripts, observed profiles and prior reference records used in step 06.",
            ),
            row(
                "Rejected submission",
                "The previous assistant submission, preserved in the conversation; the adapter also retains provider reasoning when present.",
            ),
            row(
                "Validation feedback",
                "The tool response describing schema or evidence-location errors. The original response schema and submission/revision tools remain available.",
            ),
        ],
        outputs=["A corrected complete proposal or a patch, checked again by step 07."],
        prompt="notebook-endpoint-coverage",
        schema="coverage_protocol.py",
        note="Agreed sequence, not yet implemented: at most one repair after a rejected creation. A second failure stops and is preserved. There is no separate repair prompt file: the creation prompt plus validation feedback drives the repair. Current code still has broader turn allowances and separate output-limit recovery.",
        files=["reference_stage.py", "run_coverage.py"],
    ),
    dict(
        id="coverage-review",
        number="09",
        title="Review endpoint coverage",
        kind="llm",
        group="Endpoints",
        purpose="Independently check whether the proposal covers the notebook’s science and is grounded in observed evidence.",
        inputs=[
            row(
                "All creation evidence",
                "The same source, scripts, profiles, earlier preparation plan/review and execution records listed in step 06.",
            ),
            row(
                "Accepted endpoint proposal",
                "The complete proposal that passed step 07, after repair if needed.",
            ),
        ],
        outputs=[
            "CoverageReview: approve, revise or reject.",
            "Omitted endpoints, unsupported claims, scientific-scope changes and remaining executable validation.",
        ],
        prompt="notebook-endpoint-review",
        schema="coverage_protocol.py",
        fields=[
            "decision",
            "rationale",
            "omitted_scientific_endpoints",
            "unsupported_evidence_claims",
            "scientific_scope_changes",
            "remaining_validation",
        ],
        note="A fresh model conversation, using GLM again. It receives the accepted proposal, not the creator’s reasoning trace. Agreed sequence: one review call, with findings reported rather than another automatic repair loop. Approval allows contract drafting; it does not validate a grader.",
        files=["run_coverage.py", "coverage_protocol.py"],
    ),
]

for stage in STAGES:
    stage["links"] = [{"label": name, "url": BASE + EXP + name} for name in stage["files"]]
    if "prompt" in stage:
        path = "src/biotasks/prompts/" + stage["prompt"] + ".md"
        content = (ROOT / path).read_text()
        stage["prompt_text"] = content
        stage["prompt_url"] = BASE + path
        stage["prompt_sha256"] = hashlib.sha256(content.encode()).hexdigest()

DOCUMENTS = {}


def document(key, label, path, *, text=None, field=None):
    value = (ROOT / EXP / path).read_text() if text is None else text
    if field:
        value = json.loads(value)[field]
        value = value if isinstance(value, str) else json.dumps(value, indent=2)
    DOCUMENTS[key] = dict(label=label, path=path, text=value)
    return key


seed = json.loads((ROOT / EXP / "seeds/current.json").read_text())[0]
ref = "reference-runs/003/"
attempt = ref + "attempt-2/"
cov = "coverage-runs/001/"
ev = "pipeline-map/evidence/"
document(
    "notebook",
    "Original notebook cells · rendered text",
    "seeds/current.json",
    text=seed["question_text"],
)
document("seed", "Seed + provenance", "seeds/current.json", text=json.dumps(seed, indent=2))
document("baseline", "Converted source · baseline.py", "reference-inputs/scanpy/baseline.py")
document("conversion", "Conversion record", "reference-inputs/scanpy/conversion.json")
document("staged", "Original data files · staging receipt", ref + "staged-inputs.json")
document(
    "prepare-input", "Exact preparation input · all fields", ev + "reference-preparation-input.json"
)
document(
    "review-input",
    "Exact preparation-review input · all fields",
    ev + "reference-review-input.json",
)
document(
    "coverage-input",
    "Exact endpoint-creation input · all fields",
    ev + "endpoint-creation-input.json",
)
document(
    "used-prompt", "Endpoint prompt used in this recorded run", ev + "endpoint-creation-prompt.md"
)
for key, label, filename in [
    ("plan", "GLM preparation plan", "plan.json"),
    ("review", "GLM preparation review", "review.json"),
    ("script", "Executed source · reference.py", "reference.py"),
    ("diff", "Changes to the converted source", "source.diff"),
    ("setup", "Generated dependency/setup script", "setup.sh"),
    ("execution", "Reference execution result", "execution.json"),
    ("stdout", "Reference stdout/stderr", "reference.log"),
    ("inventory", "Exported files · sizes and hashes", "artifacts.json"),
    ("environment", "Resolved dependencies", "environment.txt"),
]:
    document(key, label, attempt + filename)
document("profiles", "All observed file profiles", cov + "profiles/all.json")
document("inspection", "Inspection outcome", cov + "inspection.json")
document("retrieval", "Retrieved file identities", cov + "retrieval.json")
document("coverage-result", "Endpoint-creation outcome · incomplete", cov + "result.json")
document("coverage-summary", "Request outcomes and token usage", cov + "summary.json")
profiles = json.loads(DOCUMENTS["profiles"]["text"])
profile_keys = []
for i, profile in enumerate(profiles):
    profile_keys.append(
        document(
            f"profile-{i}",
            profile["path"] + " · observed profile",
            cov + "profiles/" + profile["path"] + ".profile.json",
        )
    )

RECORDS = {
    "convert": (
        ["notebook", "seed"],
        ["baseline", "conversion"],
        "Actual source conversion",
        "The input pane shows notebook cells rendered as text; the output pane is the actual complete plain Python script. Conversion did not execute it.",
    ),
    "prepare": (
        ["prepare-input", "notebook", "baseline", "staged"],
        ["plan", "setup", "script", "diff"],
        "Reference campaign 003 · preparation pass 2",
        "This is the final successful preparation pass, after earlier setup/dependency failures. Its exact input includes the earlier feedback. The plan is GLM output; the script and diff are materialized programmatically from that plan.",
    ),
    "reference-review": (
        ["review-input", "plan", "diff"],
        ["review"],
        "Reference campaign 003 · review pass 2",
        "The review was made before execution. Its approval is a static assessment; future-tense checks in it are not measured results.",
    ),
    "execute": (
        ["script", "setup", "staged"],
        ["execution", "stdout", "inventory", "environment"],
        "Reference campaign 003 · successful attempt 2",
        "The full analysis completed in 136.55 seconds and exported eight files. The large biological files are retained remotely, not embedded here. Their actual profiles are available in step 05; this viewer does not reconstruct CSV rows from per-column examples.",
    ),
    "inspect": (
        ["inventory", "retrieval"],
        ["inspection", *profile_keys, "profiles"],
        "Coverage campaign 001 · observed profiles",
        "These are measured profiles of the eight saved reference files. CSV examples are independent samples per column, not aligned row previews. HDF5 previews are partial; full matrices are not displayed.",
    ),
    "create": (
        ["coverage-input", "used-prompt", "notebook", "script", "profiles"],
        ["coverage-result", "coverage-summary"],
        "Coverage campaign 001 · no accepted proposal",
        "Both responses hit the 32,000-token limit. No endpoint proposal was accepted. These are controller outcome records, not a successful model output. The exact prompt used in that run differs from the current template shown below.",
    ),
    "check": (
        [],
        [],
        "Not reached for a complete endpoint proposal",
        "The adapter rejected the truncated responses before an endpoint proposal reached schema/evidence validation. There is no validation result to display for this step.",
    ),
    "repair": (
        [],
        [],
        "New one-repair sequence has not run",
        "The earlier run made an output-limit recovery request, not the newly agreed repair of a proposal rejected by programmatic checks. No input/output pair exists for this new step yet.",
    ),
    "coverage-review": (
        [],
        [],
        "Not run",
        "Endpoint creation did not produce an accepted proposal, so the independent coverage review was never called. There is no review response to display.",
    ),
}
for stage in STAGES:
    inputs, outputs, label, explanation = RECORDS[stage["id"]]
    stage["record"] = dict(inputs=inputs, outputs=outputs, label=label, explanation=explanation)

FORMATTER = HtmlFormatter(nowrap=True, style="friendly")
LEXERS = {
    "python": PythonLexer,
    "shell": BashLexer,
    "diff": DiffLexer,
    "json": JsonLexer,
    "markdown": MarkdownLexer,
    "text": TextLexer,
}
FIELD_LANGUAGES = {
    "baseline_script": "python",
    "executed_script": "python",
    "source_diff": "diff",
    "setup_sh": "shell",
    "before": "python",
    "after": "python",
}


def colored(text, language):
    """Escape and highlight during the build; the viewer needs no CDN or lexer."""
    if language == "notebook":
        parts = re.split(r"(--- (?:code|markdown) cell \d+ ---\n)", text)
        output = [html.escape(parts[0])]
        for index in range(1, len(parts), 2):
            marker, body = parts[index : index + 2]
            output.append('<span class="c">' + html.escape(marker) + "</span>")
            output.append(colored(body, "python" if "code cell" in marker else "markdown"))
        return "".join(output)
    lexer = LEXERS[language](stripnl=False, ensurenl=False)
    result = highlight(text, lexer, FORMATTER)
    # HtmlFormatter terminates its last output line; preserve source text exactly.
    if not text.endswith("\n") and result.endswith("\n"):
        result = result[:-1]
    return result


def code(text, language="text"):
    return '<pre class="syntax">' + colored(text, language) + "</pre>"


def structured(value, key="", depth=0):
    if not isinstance(value, (dict, list)):
        if isinstance(value, str):
            language = "notebook" if key == "question_text" else FIELD_LANGUAGES.get(key, "text")
            return code(value, language)
        return code(json.dumps(value), "json")
    if (
        depth >= 5
        or isinstance(value, list)
        and all(not isinstance(item, (dict, list)) for item in value)
    ):
        return code(json.dumps(value, indent=2), "json")
    entries = value.items() if isinstance(value, dict) else enumerate(value)
    output = []
    for name, item in entries:
        label = html.escape(str(name))
        complex_value = isinstance(item, (dict, list)) or isinstance(item, str) and len(item) > 180
        if complex_value:
            unit = (
                "fields"
                if isinstance(item, dict)
                else "items"
                if isinstance(item, list)
                else "characters"
            )
            output.append(
                f"<details><summary>{label} · {len(item):,} {unit}</summary>"
                + structured(item, str(name), depth + 1)
                + "</details>"
            )
        else:
            rendered = (
                html.escape(item) if isinstance(item, str) else colored(json.dumps(item), "json")
            )
            output.append(f'<div class="scalar syntax"><b class="nt">{label}:</b> {rendered}</div>')
    return "".join(output)


for key, doc in DOCUMENTS.items():
    try:
        doc["html"] = structured(json.loads(doc["text"]))
    except json.JSONDecodeError:
        language = {".py": "python", ".sh": "shell", ".diff": "diff", ".md": "markdown"}.get(
            Path(doc["path"]).suffix, "text"
        )
        doc["html"] = code(doc["text"], "notebook" if key == "notebook" else language)
for stage in STAGES:
    if "prompt_text" in stage:
        stage["prompt_html"] = colored(stage["prompt_text"], "markdown")

template = (HERE / "template.html").read_text()
data = json.dumps(STAGES, ensure_ascii=False).replace("<", "\\u003c")
documents = json.dumps(DOCUMENTS, ensure_ascii=False).replace("<", "\\u003c")
(HERE / "index.html").write_text(
    template.replace("__STAGE_DATA__", data)
    .replace("__DOCUMENT_DATA__", documents)
    .replace("__SYNTAX_CSS__", FORMATTER.get_style_defs(".syntax"))
)
print("Built", HERE / "index.html")
