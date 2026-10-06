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
# Escaping '<' prevents even a source-provided closing script tag from breaking out.
payload = json.dumps(catalog, ensure_ascii=True).replace("<", "\\u003c")
template = (root / "template.html").read_text()
assert template.count("__CATALOG__") == 1
(root / "index.html").write_text(template.replace("__CATALOG__", payload))
print(f"Built explorer for {len(catalog['sources'])} candidate analyses")
