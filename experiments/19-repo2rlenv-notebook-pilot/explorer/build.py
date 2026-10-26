"""Build the latest standalone explorer using only versioned, selected evidence."""

import argparse
import hashlib
import html
import json
import subprocess
from pathlib import Path

from markdown_it import MarkdownIt
from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import TextLexer, get_lexer_by_name
from pygments.util import ClassNotFound

HERE = Path(__file__).resolve().parent
EXP = HERE.parent
ROOT = EXP.parents[1]
REV = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
BASE = f"https://github.com/Open-Athena/biotasks/blob/{REV}/"
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--profile", type=Path, default=HERE / "current.json")
parser.add_argument("--output", type=Path, default=HERE)
args = parser.parse_args()
profile_path = args.profile.resolve()
profile_path.relative_to(ROOT)
profile = json.loads(profile_path.read_text())
OUTPUT = args.output.resolve()
OUTPUT.mkdir(parents=True, exist_ok=True)
release = profile.get("release")
RELEASE = None
md = MarkdownIt("commonmark", {"html": False}).enable("table")
formatter = HtmlFormatter(style="monokai", noclasses=True)
sources = {
    "repo:" + str(profile_path.relative_to(ROOT)): hashlib.sha256(
        profile_path.read_bytes()
    ).hexdigest()
}


def code(text, language="text"):
    try:
        lexer = get_lexer_by_name(language)
    except ClassNotFound:
        lexer = TextLexer()
    return highlight(text, lexer, formatter)


def content(text, suffix):
    if suffix == ".md":
        return '<div class="markdown">' + md.render(text) + "</div>"
    language = {
        ".py": "python",
        ".json": "json",
        ".ipynb": "json",
        ".jsonl": "json",
        ".r": "r",
        ".R": "r",
        ".toml": "toml",
        ".sh": "bash",
        ".diff": "diff",
    }.get(suffix, "text")
    return code(text, language)


def artifact(relative, label=None, opened=False):
    path = ((ROOT / relative[5:]) if relative.startswith("repo:") else (EXP / relative)).resolve()
    path.relative_to(ROOT)
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
    body = f'<article class="panel stage" id="{html.escape(key)}"><span class="pill">{html.escape(kind)}</span><h2>{html.escape(title)}</h2><p>{html.escape(description)}</p>'
    revision = profile.get("program_revisions", {}).get(key, profile.get("runtime_revision", REV))
    program_base = f"https://github.com/Open-Athena/biotasks/blob/{revision}/"
    body += f'<p>Program: <a href="{program_base}{program if program.startswith("src/") else str(EXP.relative_to(ROOT)) + "/" + program}">{program}</a></p>'
    for heading, files in groups:
        body += f"<h3>{heading}</h3>" + "".join(artifact(path, label) for path, label in files)
    return body + "</article>"


def files(prefix, *names):
    return [(prefix + "/" + name, name) for name in names]


stages = profile["stages"]
stage_ids = [item[0] for item in stages]
if len(set(stage_ids)) != len(stage_ids) or set(stage_ids) & {
    "notebook",
    "task",
    "attempt",
    "pipeline",
    "review",
}:
    raise ValueError("Pipeline stage IDs must be unique and distinct from view IDs")


def evidence_json(relative):
    path = EXP / relative
    sources[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
    return json.loads(path.read_text())


seeds = evidence_json(profile["seed"])
if len(seeds) != 1:
    raise ValueError("Select one explicit notebook seed for this explorer")
seed = seeds[0]
notebook = evidence_json(profile["notebook"])
if release:
    RELEASE = evidence_json(release["publication"])["commit_sha"]
    release_url = "https://huggingface.co/datasets/" + release["repository"] + "/tree/" + RELEASE
    release_label = "Published dataset ↗"
else:
    release_url, release_label = seed["url"], "Source notebook ↗"
language = profile.get(
    "notebook_language",
    notebook.get("metadata", {}).get("kernelspec", {}).get("language", "python"),
)
cells = []
for i, cell in enumerate(notebook["cells"]):
    text = "".join(cell["source"])
    rendered = content(text, ".md") if cell["cell_type"] == "markdown" else code(text, language)
    cells.append(
        f'<div class="cell"><small>Cell {i + 1} · {html.escape(cell["cell_type"])}</small>'
        + rendered
        + "</div>"
    )
notebook_html = (
    "<h2>"
    + html.escape(profile["notebook_title"])
    + "</h2><p>"
    + html.escape(profile["notebook_description"])
    + f' <a href="{html.escape(seed["url"])}">Pinned source notebook</a>.</p><p>Source cells below; saved notebook outputs are not shown as fresh results.</p>'
)
notebook_html += (
    artifact(profile["notebook"], "Actual notebook JSON")
    + artifact(profile["converted"], "Converted script")
    + "".join(cells)
)
question_state = (
    "published solver question"
    if release
    else "generated question; scientific validation is not yet complete"
)
task_html = (
    "<h2>"
    + html.escape(profile["task_title"])
    + "</h2><p>The "
    + question_state
    + " is below. Reference answers and grading code are separate from solver inputs.</p>"
)
task_html += artifact(profile["instruction"], "Solver question", True)
for key, label in [
    ("task_manifest", "Input and reference artifact manifest"),
    ("task_config", "Harbor environment and limits"),
    ("task_outputs", "Output artifacts and exact downloads (inspection only)"),
]:
    if profile.get(key):
        task_html += artifact(profile[key], label)
task_html += "<h3>Private grading assets (inspection only)</h3>"
for key, label in [("grader", "Deterministic grader"), ("oracle", "Reference solution")]:
    if profile.get(key):
        task_html += artifact(profile[key], label)
trajectory_path, trajectory = None, {"steps": []}
native_summary = evidence_json(profile["native_summary"]) if profile.get("native_summary") else None
if profile.get("trajectory_glob"):
    matches = list(EXP.glob(profile["trajectory_glob"]))
    if len(matches) != 1:
        raise ValueError("Select exactly one solver trajectory")
    trajectory_path = matches[0]
    trajectory = evidence_json(str(trajectory_path.relative_to(EXP)))
attempt_html = "<h2>Blind solver attempt</h2>"
if native_summary:
    solver = native_summary["solver"]
    attempt_html += f"<p>{html.escape(solver['agent'])} · {html.escape(profile.get('solver_model', 'GLM-5.3'))} · reward <strong>{html.escape(str(solver['reward']))}</strong>. The task environment was an offline CPU sandbox; recorded attempt evidence is below.</p>"
    if solver.get("exception_type"):
        attempt_html += (
            f"<p>Recorded outcome: <strong>{html.escape(solver['exception_type'])}</strong>.</p>"
        )
else:
    attempt_html += "<p>No blind solver attempt is recorded for this selected task yet.</p>"
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
# Omit model reasoning from the reading view; retain the original linked record.
if trajectory_path:
    attempt_html += (
        f'<p><a href="{BASE}{trajectory_path.relative_to(ROOT)}">Full recorded trajectory</a></p>'
    )
    for name in ["result.json", "verifier/report.json"]:
        selected = profile.get("trial_result") if name == "result.json" else None
        selected = selected or str((trajectory_path.parent.parent / name).relative_to(EXP))
        label = profile.get("trial_result_label") if name == "result.json" else None
        attempt_html += artifact(selected, label or Path(selected).name)
review_html = "<h2>Validation and release</h2>"
if profile.get("grading_controls"):
    controls = evidence_json(profile["grading_controls"])
    passed = sum(item["passed_control"] is True for item in controls)
    review_html += f"<p>{passed} of {len(controls)} scientific controls passed.</p>"
else:
    review_html += "<p>Scientific validation is not yet complete.</p>"
if native_summary:
    review_html += (
        "<p>Native controls: "
        + ", ".join(
            html.escape(str(c["agent"])) + " reward " + html.escape(str(c["reward"]))
            for c in native_summary["controls"]
        )
        + ".</p>"
    )
review_html += "<p>" + html.escape(profile["review_description"]) + "</p>"
for path in profile["review_files"]:
    review_html += artifact(path)
pipeline_html = '<h2>Notebook → task → attempt</h2><p>Prompts, inputs and outputs selected for this task. Model output is separate from prompt text. Expand a document to inspect it; large biological files are represented by manifests and available in the release.</p><div class="stage-nav">'
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
    .replace("__RELEASE__", html.escape(release_url))
    .replace("__RELEASE_LABEL__", html.escape(release_label))
    .replace("__SUBTITLE__", html.escape(profile["subtitle"]))
    .replace("__FOOTER__", html.escape(profile["footer"]))
)
(OUTPUT / "index.html").write_text("\n".join(line.rstrip() for line in page.split("\n")))
(OUTPUT / "source-manifest.json").write_text(
    json.dumps(
        {
            "evidence_revision": REV,
            "release_revision": RELEASE,
            "runtime_revision": profile.get("runtime_revision"),
            "program_revisions": profile.get("program_revisions", {}),
            "profile": str(profile_path.relative_to(ROOT)),
            "stage_ids": [s[0] for s in stages],
            "has_solver_trajectory": trajectory_path is not None,
            "solver_steps": len(trajectory["steps"]),
            "solver_tool_steps": sum(bool(s.get("tool_calls")) for s in trajectory["steps"]),
            "files": sources,
        },
        indent=2,
    )
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
