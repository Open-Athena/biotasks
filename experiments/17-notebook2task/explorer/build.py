"""Build a self-contained HTMLPreview-compatible explorer; no network required."""
import json
import hashlib
import html
from markdown_it import MarkdownIt
from pathlib import Path

root = Path(__file__).resolve().parent
catalog = json.loads((root / "catalog.json").read_text())
assert len({r["id"] for r in catalog["sources"]}) == len(catalog["sources"])
for row in catalog["sources"]:
    for key in ("source_url", "read_url"):
        assert row[key].startswith("https://"), (row["id"], key)
    if row["prior"]:
        assert row["prior"]["url"].startswith("https://github.com/")
        assert all(s["url"].startswith("https://") for s in row["prior"]["record"]["sources"])
for row in catalog["sources"]:
    if row["id"] == "dnase":
        original = (root / "snapshots/bedtools.md").read_text()
        license_text = (root / "snapshots/bedtools-LICENSE.txt").read_text()
        row["snapshot_sha256"] = hashlib.sha256(original.encode()).hexdigest()
        row["snapshot_html"] = ('<!doctype html><html><head><meta charset="utf-8">'
            '<base target="_blank"><style>body{font:15px/1.6 system-ui;padding:22px;max-width:900px;margin:auto}'
            'pre{overflow:auto;background:#f3f5f4;padding:12px}img{max-width:100%}a{color:#087b77}</style></head><body>'
            '<p>Original bedtools tutorial by Aaron Quinlan. MIT-licensed source snapshot; no code executed.</p>'
            + MarkdownIt("commonmark", {"html": False}).render(original)
            + '<hr><pre>' + html.escape(license_text) + '</pre></body></html>')
# Published reference examples are separate from source candidates.
comparison_root = root / "comparisons"
catalog["comparisons"] = json.loads((comparison_root / "cases.json").read_text())
md = MarkdownIt("commonmark", {"html": False})
for case in catalog["comparisons"]:
    pilot_name = {"seta-cytopathology": "seta-cytopathology-retry", "bix-asxl1": "bix-asxl1"}[case["id"]]
    pilot = root.parent / "runs/20261006-seta-v1-pilot" / pilot_name
    case["baseline_draft"] = (pilot / "draft_spec.md").read_text()
    case["baseline_status"] = "Rejected by multi-model gate" if case["id"] == "bix-asxl1" else "Draft produced; changed to frozen-model evaluation; not validated"
    glm = root.parent / "runs/20261006-glm53-seta-v1-budget-retry/results" / case["id"]
    case["glm_initial_status"] = "Context ceiling reached; no draft" if case["id"] == "seta-cytopathology" else "Output ceiling reached in reasoning; no draft (raw runner status corrected)"
    if (glm / "summary.json").exists():
        case["glm_summary"] = json.loads((glm / "summary.json").read_text())
        draft = glm / "artifacts/draft_spec.md"
        final = glm / "last-message.md"
        case["glm_output"] = draft.read_text() if draft.exists() else ((final.read_text() or "No draft or final response was written.") if final.exists() else "No draft or final response was written.")
    if "instruction_file" in case:
        case["instruction"] = (comparison_root / case["instruction_file"]).read_text()
    if "question_file" in case:
        question = json.loads((comparison_root / case["question_file"]).read_text())
        case["instruction"] = question["question"]
        case["reference_answer"] = question["ideal"]
        case["canary"] = question["canary"]
    if "notebook_file" in case:
        notebook = json.loads((comparison_root / case["notebook_file"]).read_text())
        cells = []
        for number, cell in enumerate(notebook["cells"]):
            source = "".join(cell["source"])
            body = md.render(source) if cell["cell_type"] == "markdown" else "<pre>" + html.escape(source) + "</pre>"
            for output in cell.get("outputs", []):
                text = output.get("text", output.get("data", {}).get("text/plain", ""))
                if not text and output.get("output_type") == "error":
                    text = output.get("traceback", [])
                if not text:
                    text = str(output.get("data", {}))
                body += '<pre class="output">' + html.escape("".join(text)) + '</pre>'
            cells.append(f'<section><small>Cell {number} · {cell["cell_type"]}</small>{body}</section>')
        case["notebook_html"] = ('<!doctype html><html><head><meta charset="utf-8"><style>'
            'body{font:15px/1.6 system-ui;padding:20px}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#f3f6f4;padding:12px}'
            'section{border-bottom:1px solid #ddd;padding:15px 0}.output{background:#fff8e9}a{color:#087b77}</style></head><body>'
            '<h1>BixBench original capsule notebook</h1><p>FutureHouse · Apache-2.0 · Saved outputs; not rerun.</p>'
            + ''.join(cells) + '</body></html>')
# Escaping '<' prevents even a source-provided closing script tag from breaking out.
payload = json.dumps(catalog, ensure_ascii=True).replace("<", "\\u003c")
template = (root / "template.html").read_text()
assert template.count("__CATALOG__") == 1
(root / "index.html").write_text(template.replace("__CATALOG__", payload))
print(f"Built explorer for {len(catalog['sources'])} candidate analyses")
