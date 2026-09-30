"""Bounded structural audit of this research draft; no scientific validation."""

from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[2]
DOCS = ROOT / "docs/improvements"
catalog = (DOCS / "README.md").read_text()
bibliography = (DOCS / "sources.md").read_text()
entry_pairs = re.findall(
    r"^### (I\d+)\n(.*?)(?=^### |^## |\Z)", catalog, re.M | re.S
)
source_pairs = re.findall(
    r"^### ([BS]\d+)\n(.*?)(?=^### |^## |\Z)", bibliography, re.M | re.S
)
entries = dict(entry_pairs)
sources = dict(source_pairs)
assert len(entries) == len(entry_pairs) == 50
assert set(entries) == {f"I{i:02}" for i in range(1, 51)}
assert len(sources) == len(source_pairs) == 45
assert set(sources) == {f"B{i:02}" for i in range(1, 35)} | {
    f"S{i:02}" for i in range(1, 12)
}

hypotheses = set()
for entry, body in entries.items():
    for field in ("**Scope:", "**Opportunity", "**Evidence and conditions:"):
        assert field in body, (entry, field)
    assert re.search(r"\b(documented|inferred)\b", body), entry
    refs = re.findall(r"sources\.md#([bs]\d+)", body)
    if "**unvalidated hypothesis**" in body:
        hypotheses.add(entry)
        for field in ("**Origin:**", "**Validation needed:**"):
            assert field in body, (entry, field)
    else:
        assert refs, entry
    for ref in refs:
        assert ref.upper() in sources, (entry, ref)
        assert f"README.md#{entry.lower()}" in sources[ref.upper()], (entry, ref)
    assert f"](#{entry.lower()})" in catalog.split("## Identifiers")[0], entry

assert hypotheses == {"I49", "I50"}

for source, body in sources.items():
    assert "https://" in body and "Access:" in body, source
    assert f"sources.md#{source.lower()}" in catalog, source


def anchors(path):
    headings = re.findall(r"^#{1,6} (.+)$", path.read_text(), re.M)
    return {
        re.sub(r"[^\w\- ]", "", h.lower()).replace(" ", "-")
        for h in headings
    }


files = list(DOCS.glob("*.md")) + [
    ROOT / "docs/README.md",
    Path(__file__).with_name("logbook.md"),
]
link_count = 0
for path in files:
    contents = path.read_text()
    assert contents.endswith("\n"), path
    assert not re.search(r"[ \t]+$", contents, re.M), path
    for target in re.findall(r"\[[^\]]+\]\(([^)]+)\)", contents):
        if target.startswith(("http://", "https://")):
            continue
        file_part, _, anchor = target.partition("#")
        dest = (path.parent / file_part).resolve() if file_part else path
        assert dest.is_file(), (path, target)
        if anchor:
            assert anchor in anchors(dest), (path, target)
        link_count += 1

assert "improvements/README.md" in (ROOT / "docs/README.md").read_text()
assert not (ROOT / "docs/pitfalls").exists()
print("PASS: 50 unique entries (48 sourced, 2 hypotheses) and 45 unique sources; expected IDs and fields.")
print("PASS: indexed navigation; reciprocal source mapping where cited; hypothesis origin/validation fields.")
print(f"PASS: {link_count} local links/anchors and Markdown whitespace.")
print("External links were inspected during research, not batch re-fetched.")
print("This audit does not test scientific claims or reproduce source analyses.")
