"""Build a read-only Notebook → Task → Attempt intake view; no external assets."""

import argparse
import html
import json
from pathlib import Path


def build(manifest, intake, output, campaign=None):
    seeds = json.loads(manifest.read_text())["seeds"]
    records = {r["id"]: r for r in json.loads(intake.read_text())["seeds"]}
    state = json.loads(campaign.read_text()) if campaign else {"seeds": []}
    stages = {s["id"]: s for s in state["seeds"]}
    base = campaign.parent if campaign else manifest.parent

    def evidence(relative):
        path = (base / relative).resolve()
        if not path.is_relative_to(base.resolve()):
            raise ValueError("Evidence path escapes campaign directory")
        return path.read_text()

    def authoring(run):
        result = json.loads(evidence(run["result"]))
        requests = result.get("requests", [])
        usage = [r["usage"] for r in requests if r.get("usage")]
        summary = {
            "run": run["id"],
            "stage": result.get("stage"),
            "outcome": result.get("outcome", "see review"),
            "exit_code": result.get("exit_code"),
            "seconds": result.get("elapsed_seconds"),
            "model_requests": len(requests),
            "requests_with_usage": len(usage),
            "recorded_input_tokens": sum(u.get("prompt_tokens", 0) for u in usage)
            if usage
            else None,
            "recorded_output_tokens": sum(u.get("completion_tokens", 0) for u in usage)
            if usage
            else None,
            "usage_complete": bool(requests) and len(usage) == len(requests),
            "inference_service": "existing free service",
            "orchestration_cost": "not measured",
        }
        parts = [
            "<h3>Authoring evidence</h3><pre>"
            + html.escape(json.dumps(summary, indent=2))
            + "</pre>"
        ]
        if run.get("review"):
            parts.append("<pre>" + html.escape(evidence(run["review"])) + "</pre>")
        if run.get("candidate"):
            files = json.loads(evidence(run["candidate"]))
            parts.append(
                f"<h3>Candidate version {run['candidate_version']} · unaccepted draft</h3>"
            )
            for name, content in files.items():
                parts.append(
                    "<details><summary>"
                    + html.escape(name)
                    + "</summary><pre>"
                    + html.escape(content)
                    + "</pre></details>"
                )
        return "".join(parts)

    cards = []
    for seed in seeds:
        row = records[seed["id"]]
        stage = stages.get(seed["id"], {})
        e = html.escape
        source = intake.parent / seed["id"] / "seed.txt"
        text = source.read_text() if source.exists() else "Source unavailable; see intake status."
        cards.append(
            f'<article id="{e(seed["id"])}"><h2>{e(seed["domain"])} · {e(seed["label"])}</h2>'
            f'<p class="status">Intake: {e(row["status"])} · Task: '
            f"{e(stage.get('status', 'not_authored'))}</p>"
            "<details><summary>Notebook</summary>"
            f'<p><a href="{e(seed["url"], quote=True)}">Pinned source</a></p>'
            f"<p>{e(seed['focus'])}</p><p>{e(seed['input_origin'])}</p>"
            f"<pre>{e(text)}</pre></details>"
            "<details><summary>Task</summary>"
            + (
                "".join(authoring(run) for run in stage.get("authoring_runs", []))
                or "<p>No generated task. Authoring and scientific validation remain pending.</p>"
            )
            + "</details><details><summary>Attempt</summary>"
            + (
                "<pre>" + e(json.dumps(stage["solver_attempts"], indent=2)) + "</pre>"
                if stage.get("solver_attempts")
                else "<p>No solver attempt or score.</p>"
            )
            + "</details></article>"
        )
    output.write_text(
        '<!doctype html><html lang="en"><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<meta http-equiv="Content-Security-Policy" content="default-src &#39;none&#39;; '
        'style-src &#39;unsafe-inline&#39;">'
        "<title>Notebook pipeline v1 · intake</title><style>"
        "body{font:16px/1.5 system-ui;max-width:1100px;margin:32px auto;padding:0 20px;"
        "background:#f6f8f7;color:#183632}article{background:white;border:1px solid #cddbd7;"
        "border-radius:10px;padding:20px;margin:20px 0}summary{cursor:pointer;font-weight:600;"
        "padding:12px 0}pre{white-space:pre-wrap;overflow-wrap:anywhere;max-height:550px;"
        "overflow:auto;background:#f6f8f7;padding:16px}.status{color:#51635e}a{color:#087b77}"
        "</style><h1>Notebook → Task → Attempt</h1><p>Ten proposed seeds. "
        "Authoring drafts and infrastructure tests are not accepted biological tasks. "
        "This campaign is incomplete; pending seeds remain in the denominator.</p>"
        + "".join(cards)
        + "</html>"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--intake", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--campaign", type=Path, default=Path(__file__).with_name("campaign.json"))
    args = parser.parse_args()
    build(Path(__file__).with_name("seeds.json"), args.intake, args.output, args.campaign)
