"""Build a static evidence explorer from explicitly selected local run archives."""

import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
EXPERIMENT = HERE.parent
ROOT = EXPERIMENT.parents[1]
FINAL = Path("/tmp/biotasks19-pilot-018-results")


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
for campaign in (9, 18):
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
for campaign in (9, 11, 13, 16, 18):
    root = Path(f"/tmp/biotasks19-pilot-{campaign:03d}-results")
    path = root / "pilot/quality/result.json"
    if not path.is_file():
        continue
    quality = read(path)
    for trial in quality["trials"]:
        if trial["role"] != "rollout" and campaign != 18:
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
encoded = json.dumps(data, ensure_ascii=False).replace("<", "\\u003c")
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
