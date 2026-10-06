"""Build a self-contained HTMLPreview-compatible explorer; no network required."""
import json
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
# Escaping '<' prevents even a source-provided closing script tag from breaking out.
payload = json.dumps(catalog, ensure_ascii=True).replace("<", "\\u003c")
template = (root / "template.html").read_text()
assert template.count("__CATALOG__") == 1
(root / "index.html").write_text(template.replace("__CATALOG__", payload))
print(f"Built explorer for {len(catalog['sources'])} candidate analyses")
