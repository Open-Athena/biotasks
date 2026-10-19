"""Build the latest standalone explorer using only versioned, selected evidence."""

import hashlib
import html
import json
import subprocess
from pathlib import Path

from markdown_it import MarkdownIt
from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import get_lexer_by_name

HERE = Path(__file__).resolve().parent
EXP = HERE.parent
ROOT = EXP.parents[1]
REV = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
BASE = f"https://github.com/Open-Athena/biotasks/blob/{REV}/"
HF = "https://huggingface.co/datasets/gonzalobenegas/biotasks-notebook-pilot-issue-19"
RELEASE = json.loads((EXP / "scientific-releases/001/publication.json").read_text())["commit_sha"]
md = MarkdownIt("commonmark", {"html": False}).enable("table")
formatter = HtmlFormatter(style="monokai", noclasses=True)
sources = {}


def code(text, language="text"):
    return highlight(text, get_lexer_by_name(language), formatter)


def content(text, suffix):
    if suffix == ".md":
        return '<div class="markdown">' + md.render(text) + "</div>"
    language = {
        ".py": "python",
        ".json": "json",
        ".ipynb": "json",
        ".toml": "toml",
        ".sh": "bash",
        ".diff": "diff",
    }.get(suffix, "text")
    return code(text, language)


def artifact(relative, label=None, opened=False):
    path = EXP / relative
    text = path.read_text()
    sources[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
    title = html.escape(label or path.name)
    url = BASE + str(path.relative_to(ROOT))
    return (
        f"<details{' open' if opened else ''}><summary>{title}</summary>"
        f'<p class="meta"><a href="{url}">{html.escape(relative)}</a></p>'
        f'<div class="document">{content(text, path.suffix)}</div></details>'
    )


def stage(key, title, kind, description, program, groups):
    body = f'<article class="panel stage" id="{key}"><span class="pill">{kind}</span><h2>{title}</h2><p>{description}</p>'
    body += f'<p>Program: <a href="{BASE}{program if program.startswith("src/") else "experiments/19-repo2rlenv-notebook-pilot/" + program}">{program}</a></p>'
    for heading, files in groups:
        body += f"<h3>{heading}</h3>" + "".join(artifact(path, label) for path, label in files)
    return body + "</article>"


def files(prefix, *names):
    return [(prefix + "/" + name, name) for name in names]


stages = [
    (
        "convert",
        "01 · Convert notebook",
        "Programmatic",
        "Pinned notebook JSON → Jupytext py:nomarker script. Markdown cells become comments. Stored notebook outputs are not execution evidence.",
        "src/biotasks/notebook_script.py",
        [
            ("Input", files("reference-inputs/scanpy", "clustering.ipynb")),
            ("Output", files("reference-inputs/scanpy", "baseline.py", "conversion.json")),
        ],
    ),
    (
        "prepare",
        "02 · Select and export terminal results",
        "GLM-5.3",
        "Preparation 010 appends export code to the original analysis. It does not install dependencies or stage data.",
        "run_preparation.py",
        [
            ("Recorded prompt", files("preparation-runs/010/prepare", "system-prompt.md")),
            ("Input", files("preparation-runs/010/prepare", "input.json")),
            (
                "Output",
                files(
                    "preparation-runs/010", "exports.py", "plan.md", "reference.py", "source.diff"
                ),
            ),
        ],
    ),
    (
        "setup",
        "03 · Set up and test reference",
        "GLM-5.3 + execution",
        "Setup 001 uses tools to prepare dependencies and real inputs, then tests the reference offline. The controller executes the script; GLM diagnoses setup issues.",
        "run_reference_setup.py",
        [
            ("Recorded prompt", files("setup-runs/001", "system-prompt.md")),
            (
                "Input",
                [("explorer/evidence/setup-input.json", "Initial messages and available tools")],
            ),
            (
                "Output",
                files(
                    "setup-runs/001/candidate",
                    "pyproject.toml",
                    "system-packages.json",
                    "stage-inputs.sh",
                    "analysis.py",
                )
                + files("setup-runs/001/trial", "reference.py", "result.json", "reference.log")
                + files("setup-runs/001", "output-audit.json"),
            ),
        ],
    ),
    (
        "replay",
        "04 · Replay reference",
        "Programmatic",
        "Replay 001 checks the prepared reference against frozen inputs. No new model prompt.",
        "run_reference_replay.py",
        [
            ("Input", files("replay-runs/001/replay", "frozen-inputs.json", "setup.sh")),
            (
                "Output",
                files("replay-runs/001/replay", "comparison.json")
                + files("replay-runs/001", "result.json"),
            ),
        ],
    ),
    (
        "specify",
        "05 · Specify scientific task",
        "GLM-5.3",
        "Specification 016 selects marker statistics with supplied group labels and stable gene identities. The solver need not reproduce clustering or UMAP.",
        "run_specification.py",
        [
            ("Recorded prompt", files("specification-runs/016/specify", "system-prompt.md")),
            (
                "Input",
                [("explorer/evidence/specification-input.json", "Exact recorded worker input")],
            ),
            (
                "Output",
                files(
                    "specification-runs/016",
                    "task-brief.md",
                    "validation-handoff.md",
                    "specification.json",
                ),
            ),
        ],
    ),
    (
        "materialize",
        "06 · Materialize inputs and oracle",
        "GLM-5.3 + execution",
        "Materialization 006 produces four public inputs and a private reference. The original matrices are observed data; fixed labels and identities are derived inputs.",
        "task_materialization.py",
        [
            ("Recorded prompt", files("materialization-runs/006", "system-prompt.md")),
            (
                "Input",
                [("explorer/evidence/materialization-input.json", "Exact recorded worker input")],
            ),
            (
                "Output",
                files(
                    "materialization-runs/006",
                    "derive.py",
                    "oracle.py",
                    "manifest.json",
                    "final-execution.json",
                ),
            ),
        ],
    ),
    (
        "grade",
        "07 · Build and validate grading",
        "GLM-5.3 + deterministic controls",
        "Accepted grading 006 combines the independently authored solution and frozen probes with the repaired grader. All 19 controls were reexecuted. Below are the component prompts, not a claim that this was one model call.",
        "grading_session.py",
        [
            (
                "Recorded prompts",
                files("grading-runs/002/grader", "system-prompt.md")
                + files("grading-runs/005/repair", "system-prompt.md")
                + files("grading-runs/006/contract", "system-prompt.md")
                + files("grading-runs/006/review", "system-prompt.md"),
            ),
            (
                "Inputs",
                files("grading-runs/002/grader", "input.json")
                + files("grading-runs/006/contract", "input.json")
                + files("grading-runs/006", "inputs.json"),
            ),
            (
                "Outputs",
                files(
                    "grading-runs/006",
                    "grade.py",
                    "acceptance-contract.md",
                    "independent-solution.json",
                    "probes.json",
                    "final-controls.json",
                    "review.json",
                ),
            ),
        ],
    ),
    (
        "native",
        "08 · Run Harbor controls and solver",
        "Programmatic + GLM-5.3 solver",
        "Native 003: oracle reward 1, empty baseline reward 0, blind Terminus-2 / GLM-5.3 reward 1. The Attempt tab shows the actual question, tool calls and observations.",
        "run_scientific_native.py",
        [
            (
                "Input",
                files("native-runs/003", "inputs.json")
                + [("explorer/evidence/task.toml", "Published Harbor configuration")],
            ),
            (
                "Output",
                files("native-runs/003/native", "result.json")
                + files("native-runs/003", "operator-review.json"),
            ),
        ],
    ),
    (
        "release",
        "09 · Publish and download-check",
        "Programmatic",
        "The release was published publicly and independently downloaded and verified. No new LLM call.",
        "stage_scientific_release.py",
        [
            ("Input", files("scientific-releases/001", "manifest.json", "release-files.json")),
            (
                "Output",
                files("scientific-releases/001", "publication.json", "download-verification.json"),
            ),
        ],
    ),
]

seed = json.loads((EXP / "seeds/current.json").read_text())[0]
notebook = json.loads((EXP / "reference-inputs/scanpy/clustering.ipynb").read_text())
cells = []
for i, cell in enumerate(notebook["cells"]):
    text = "".join(cell["source"])
    cells.append(
        f'<div class="cell"><small>Cell {i + 1} · {cell["cell_type"]}</small>'
        + content(text, ".md" if cell["cell_type"] == "markdown" else ".py")
        + "</div>"
    )
notebook_html = f'<h2>Scanpy · Clustering and marker genes</h2><p>NeurIPS BMMC samples s1d1 and s1d3. <a href="{html.escape(seed["url"])}">Pinned source notebook</a> · BSD-3-Clause; input data CC BY 4.0.</p><p>Source cells below; saved notebook outputs are not shown as fresh results.</p>'
notebook_html += (
    artifact("reference-inputs/scanpy/clustering.ipynb", "Actual notebook JSON")
    + artifact("reference-inputs/scanpy/baseline.py", "Converted Python script")
    + "".join(cells)
)
task_html = "<h2>Marker genes for fixed cell groups</h2><p>The exact published solver question is below. Reference answers and grading code are separate from solver inputs.</p>"
task_html += artifact("explorer/evidence/instruction.md", "Solver question", True)
task_html += artifact(
    "materialization-runs/006/manifest.json", "Input and reference artifact manifest"
) + artifact("explorer/evidence/task.toml", "Harbor environment and limits")
task_html += (
    "<h3>Private grading assets (inspection only)</h3>"
    + artifact("grading-runs/006/grade.py", "Deterministic grader")
    + artifact("materialization-runs/006/oracle.py", "Reference solution")
)
trajectory_path = next((EXP / "native-runs/003/native/terminus-2").rglob("trajectory.json"))
trajectory = json.loads(trajectory_path.read_text())
attempt_html = "<h2>Blind solver attempt</h2><p>Terminus-2 · GLM-5.3 · reward <strong>1</strong> · 18 model requests · 8m 43s total trial. Tools ran in an offline CPU sandbox. All nine grading checks passed.</p>"
for step in trajectory["steps"]:
    title = "Solver input" if step["source"] == "user" else f"Turn {step['step_id'] - 1}"
    attempt_html += f"<details><summary>{title}</summary>"
    if step.get("message"):
        attempt_html += "<h3>Message</h3>" + content(step["message"], ".md")
    if step.get("tool_calls"):
        attempt_html += "<h3>Tool calls</h3>"
        for call in step["tool_calls"]:
            arguments = call.get("arguments", {})
            attempt_html += (
                '<div class="document">'
                + code(arguments.get("keystrokes", json.dumps(arguments, indent=2)), "bash")
                + "</div>"
            )
    if step.get("observation"):
        attempt_html += "<h3>Tool results</h3>"
        for result in step["observation"].get("results", []):
            attempt_html += (
                '<div class="document">' + code(str(result.get("content", ""))) + "</div>"
            )
    attempt_html += "</details>"
# Deliberately omit model reasoning from the reading view; retain the original linked record.
attempt_html += (
    f'<p><a href="{BASE}{trajectory_path.relative_to(ROOT)}">Full recorded trajectory</a></p>'
)
for name in ["result.json", "verifier/report.json"]:
    attempt_html += artifact(str((trajectory_path.parent.parent / name).relative_to(EXP)), name)
review_html = "<h2>Validation and release</h2><p>19 scientific controls passed, followed by fresh Harbor oracle, empty-baseline and blind-solver trials. This is one notebook pilot, not evidence of universal software portability. Authoring and solving used the same model family. The upstream advisory label remains unverified because its standard quality-loop profile was not run; the separate scientific and native checks are recorded below.</p>"
for path in [
    "grading-runs/006/final-controls.json",
    "grading-runs/006/review.json",
    "native-runs/003/native/result.json",
    "scientific-releases/001/download-verification.json",
    "source-license-evidence.json",
]:
    review_html += artifact(path)
pipeline_html = '<h2>Notebook → task → attempt</h2><p>Recorded prompts and artifacts used for this published task. Model output is separate from prompt text. Expand a document to inspect it; large biological files are represented by manifests and available in the release.</p><div class="stage-nav">'
pipeline_html += "".join(f'<a href="#{s[0]}">{s[1]}</a>' for s in stages) + "</div>"
pipeline_html += "".join(stage(*s) for s in stages)
sections = "".join(
    f'<section id="{key}" class="panel view">{body}</section>'
    for key, body in [
        ("notebook", notebook_html),
        ("task", task_html),
        ("attempt", attempt_html),
        ("pipeline", pipeline_html),
        ("review", review_html),
    ]
)
page = (
    (HERE / "template.html")
    .read_text()
    .replace("__STYLE__", (HERE / "style.css").read_text())
    .replace("__SECTIONS__", sections)
    .replace("__RELEASE__", HF + "/tree/" + RELEASE)
)
(HERE / "index.html").write_text(page)
(HERE / "source-manifest.json").write_text(
    json.dumps({"evidence_revision": REV, "release_revision": RELEASE, "files": sources}, indent=2)
    + "\n"
)
print(
    json.dumps(
        {
            "bytes": len(page.encode()),
            "stages": len(stages),
            "solver_steps": len(trajectory["steps"]),
            "source_files": len(sources),
        }
    )
)
