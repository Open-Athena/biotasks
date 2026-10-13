"""Build a static evidence explorer from explicitly selected local run archives."""

import argparse
import hashlib
import json
import re
from pathlib import Path

from markdown_it import MarkdownIt
from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import get_lexer_by_name

HERE = Path(__file__).resolve().parent
EXPERIMENT = HERE.parent
ROOT = EXPERIMENT.parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--campaign", type=int, default=18)
parser.add_argument("--status", type=Path, required=True)
args = parser.parse_args()
FINAL = Path(f"/tmp/biotasks19-pilot-{args.campaign:03d}-results")


def read(path):
    return json.loads(path.read_text())


def record(path, root):
    return {
        "path": str(path.relative_to(root)),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "content": read(path),
    }


q = read(FINAL / "pilot/quality/result.json")
docs = read(FINAL / "pilot/fidelity/documents.json")
seed = read(Path("/tmp/biotasks-19-scanpy-seeds.json"))[0]
data = {
    "status": read(args.status),
    "campaign": args.campaign,
    "notebook": {
        "title": seed["title"],
        "url": seed["url"],
        "revision": seed["source_revision"],
        "sha256": seed["source_sha256"],
        "text": docs["source/notebook"],
    },
    "bundle": q["bundle_hash"],
    "documents": docs,
    "calls": [],
    "attempts": [],
    "templates": {
        p.name: p.read_text() for p in (ROOT / "src/biotasks/prompts").glob("notebook-*.md")
    },
}
for campaign in dict.fromkeys((9, 18, 20, args.campaign)):
    root = Path(f"/tmp/biotasks19-pilot-{campaign:03d}-results")
    calls = sorted((root / "pilot").rglob("*.request.json"))
    for path in calls:
        if campaign == 9 and "/campaign/" not in str(path):
            continue
        entry = record(path, root)
        entry["campaign"] = campaign
        response = path.with_name(path.name.replace(".request.json", ".json"))
        entry["response"] = read(response) if response.is_file() else None
        data["calls"].append(entry)
for campaign in dict.fromkeys((9, 11, 13, 16, 18, args.campaign)):
    root = Path(f"/tmp/biotasks19-pilot-{campaign:03d}-results")
    path = root / "pilot/quality/result.json"
    if not path.is_file():
        continue
    quality = read(path)
    for trial in quality["trials"]:
        if trial["role"] != "rollout" and campaign != args.campaign:
            continue
        raw = root / trial["result"].removeprefix("/evidence/")
        if not raw.is_file():
            continue
        if hashlib.sha256(raw.read_bytes()).hexdigest() != trial["result_sha256"]:
            raise ValueError("Raw trial hash mismatch")
        saved = read(raw)
        trace = raw.parent / "agent/trajectory.json"
        data["attempts"].append(
            {
                "campaign": campaign,
                "role": trial["role"],
                "reward": trial["reward"],
                "exception": trial["exception_type"],
                "bundle": trial["bundle_hash"],
                "result_sha256": trial["result_sha256"],
                "timing": saved.get("agent_execution"),
                "probe": trial.get("probe"),
                "trajectory": read(trace) if trace.is_file() else None,
            }
        )
data["licenses"] = read(EXPERIMENT / "source-license-evidence.json")
# Same Markdown and syntax-rendering approach as issue 17, with raw HTML disabled.
md = MarkdownIt("commonmark", {"html": False}).enable("table")
formatter = HtmlFormatter(nowrap=True, noclasses=True, style="monokai")
data["rendered_markdown"] = {}
data["rendered_code"] = {}
cells = re.split(r"--- (markdown|code) cell (\d+) ---\n", data["notebook"]["text"])
for i in range(1, len(cells), 3):
    kind, _, source = cells[i : i + 3]
    if kind == "markdown":
        data["rendered_markdown"][source] = md.render(source)
    else:
        data["rendered_code"][source] = highlight(source, get_lexer_by_name("python"), formatter)
for name, source in docs.items():
    if name.endswith(".md"):
        data["rendered_markdown"][source] = md.render(source)
    if name.startswith("task/"):
        language = "python" if name.endswith(".py") else "bash" if name.endswith(".sh") else "text"
        data["rendered_code"][source] = highlight(source, get_lexer_by_name(language), formatter)


# Build readable views of model text; original request/response records stay intact.
def readable(value):
    return value.replace("\\n", "\n") if "\n" not in value and "\\n" in value else value


def render_strings(value):
    if isinstance(value, str):
        text = readable(value)
        data["rendered_markdown"][text] = md.render(text)
    elif isinstance(value, dict):
        for item in value.values():
            render_strings(item)
    elif isinstance(value, list):
        for item in value:
            render_strings(item)


for call in data["calls"]:
    payload = call.get("response")
    if isinstance(payload, dict) and isinstance(payload.get("response"), dict):
        payload = payload["response"].get("content", payload)
    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except json.JSONDecodeError:
            pass
    call["output"] = payload
    try:
        call["input"] = json.loads(call["content"].get("user", "{}"))
    except (json.JSONDecodeError, TypeError):
        call["input"] = call["content"].get("user")
    render_strings(call["content"].get("system", ""))
    render_strings(call["input"])
    render_strings(payload)
encoded = json.dumps(data, ensure_ascii=False).replace("<", "\\u003c").replace("&", "\\u0026")
page = (HERE / "template.html").read_text().replace("__DATA__", encoded)
(HERE / "index.html").write_text(page)
print(
    json.dumps(
        {
            "calls": len(data["calls"]),
            "attempts": len(data["attempts"]),
            "bytes": len(page.encode()),
        }
    )
)
