"""Build a self-contained HTMLPreview-compatible explorer; no network required."""
import json
import hashlib
import html
from markdown_it import MarkdownIt
from pathlib import Path
from urllib.parse import urljoin

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
md = MarkdownIt("commonmark", {"html": False}).enable("table").enable("strikethrough")
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
    if case["id"] == "seta-cytopathology":
        generated = root.parent / "runs/20261006-glm53-cpu-training-v1-builder-continuation/results/seta-cytopathology/artifacts"
        case["cpu_variant_instruction"] = (generated / "instruction.md").read_text()
        case["cpu_variant_tests"] = (root.parent / "validation/cpu-training-v1/candidate/tests/test_outputs.py").read_text()
        case["cpu_variant_validation"] = (root.parent / "validation/cpu-training-v1/README.md").read_text()
        case["reference_solution"] = (generated / "solution/run_pipeline.py").read_text()
        validation = root.parent / "validation/cpu-training-v1/native-02/results"
        case["validation_steps"] = json.loads((validation / "steps.json").read_text())
        case["validation_controls"] = json.loads((validation / "controls.json").read_text())
        case["validation_audit"] = json.loads((validation / "parent-audit.json").read_text())
        case["result_artifacts"] = {name: (validation / "oracle-artifacts/results" / name).read_text()
                                    for name in ["metrics.json", "selected_model_report.json", "eda.json"]}
        case["trace"] = []
        for line in (generated.parent / "events.jsonl").read_text().splitlines():
            event = json.loads(line)
            if "response" not in event:
                continue
            response = event["response"]
            choice = response["choices"][0]
            calls = []
            for call in choice["message"].get("tool_calls") or []:
                fn = call["function"]
                try:
                    args = json.loads(fn["arguments"])
                except (ValueError, TypeError):
                    args = {}
                calls.append({"tool": fn["name"], "path": args.get("path", "")})
            case["trace"].append({"turn": event["turn"], "finish": choice.get("finish_reason"),
                                  "calls": calls, "completion_tokens": response.get("usage", {}).get("completion_tokens")})

    if "instruction_file" in case:
        case["instruction"] = (comparison_root / case["instruction_file"]).read_text()
    if "question_file" in case:
        question = json.loads((comparison_root / case["question_file"]).read_text())
        case["instruction"] = question["question"]
        case["reference_answer"] = question["ideal"]
        case["canary"] = question["canary"]
    for field in ["baseline_draft", "glm_output", "cpu_variant_validation"]:
        if field not in case:
            continue
        tokens = md.parse(case[field])
        for block in tokens:
            for token in block.children or []:
                if token.type == "link_open":
                    if field == "cpu_variant_validation":
                        token.attrSet("href", urljoin(
                            "https://github.com/Open-Athena/biotasks/blob/codex/research/17-notebook2task/experiments/17-notebook2task/validation/cpu-training-v1/",
                            token.attrGet("href") or ""))
                    token.attrSet("target", "_blank")
                    token.attrSet("rel", "noopener noreferrer")
        case[field + "_html"] = md.renderer.render(tokens, md.options, {})
    case["instruction_html"] = md.render(case["instruction"])
    if case.get("cpu_variant_instruction"):
        case["cpu_variant_instruction_html"] = md.render(case["cpu_variant_instruction"])
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
# One directory and a real static detail page per source; no runtime fetch needed.
entries = [{"id": r["id"], "title": r["title"], "group": r["group"],
            "format": r["format"], "question": r["question"], "decision": r["decision"],
            "origin": "candidate", "evidence": "Proposal · not generated"} for r in catalog["sources"]]
for c in catalog["comparisons"]:
    entries.append({"id": c["id"], "title": c["title"], "group": "SETA" if c["id"].startswith("seta") else "BixBench",
                    "format": "R Markdown" if c["id"].startswith("seta") else "R notebook",
                    "decision": "Comparison only", "origin": "SETA" if c["id"].startswith("seta") else "BixBench",
                    "evidence": "Native validation · repaired recipe" if c.get("cpu_variant_instruction") else "Released task · baseline attempted"})
# Show released-task comparisons first, preserving order within each group.
entries.sort(key=lambda row: row["origin"] == "candidate")
assert len({r["id"] for r in entries}) == len(entries)
template = (root / "template.html").read_text()
assert template.count("__CATALOG__") == 1

def emit(path, payload):
    encoded = json.dumps(payload, ensure_ascii=True).replace("<", "\\u003c")
    path.parent.mkdir(exist_ok=True)
    path.write_text(template.replace("__CATALOG__", encoded))

emit(root / "index.html", {"entries": entries, "page": None, "sources": [], "comparisons": []})
for row in entries:
    emit(root / "notebooks" / (row["id"] + ".html"), {
        "entries": entries, "page": row["id"],
        "sources": [r for r in catalog["sources"] if r["id"] == row["id"]],
        "comparisons": [c for c in catalog["comparisons"] if c["id"] == row["id"]]})
print(f"Built directory and {len(entries)} notebook detail pages")
