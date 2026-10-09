"""Build a read-only Notebook → Task → Attempt intake view; no external assets."""

import argparse
import html
import json
from pathlib import Path

from convert_pi import convert


def trace_viewer(source, session_id):
    """Reuse the archived offline viewer; retain source hash and missing-call state."""
    assets = Path(__file__).with_name("explorer-assets")
    trace = json.dumps(convert(source, session_id)).replace("<", "\\u003c")
    script = (assets / "viewer.js").read_text().replace("</script", "<\\/script")
    css = (assets / "viewer.css").read_text()
    return (
        '<!doctype html><html lang="en"><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<meta http-equiv="Content-Security-Policy" content="default-src &#39;none&#39;; '
        "script-src &#39;unsafe-inline&#39;; style-src &#39;unsafe-inline&#39;; "
        'img-src data:; connect-src &#39;none&#39;">'
        "<title>Recorded Pi attempt</title><style>" + css + '</style><div id="root"></div>'
        '<script id="trajectory-data" type="application/json">'
        + trace
        + "</script><script>"
        + script
        + "</script></html>"
    )


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

    def authoring(run, stage):
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
            accepted = (
                stage.get("accepted")
                and stage.get("accepted_candidate_version") == run["candidate_version"]
            )
            label = "native validated; see packaging revision" if accepted else "unaccepted draft"
            parts.append(f"<h3>Candidate version {run['candidate_version']} · {label}</h3>")
            for name, content in files.items():
                parts.append(
                    "<details><summary>"
                    + html.escape(name)
                    + "</summary><pre>"
                    + html.escape(content)
                    + "</pre></details>"
                )
        return "".join(parts)

    def attempt(run):
        parts = ["<pre>" + html.escape(json.dumps(run, indent=2)) + "</pre>"]
        for field, title in [("summary", "Attempt summary"), ("result", "Harbor result")]:
            if run.get(field):
                parts.append(
                    "<details><summary>"
                    + title
                    + "</summary><pre>"
                    + html.escape(evidence(run[field]))
                    + "</pre></details>"
                )
        if run.get("pi_trace"):
            path = (base / run["pi_trace"]).resolve()
            if not path.is_relative_to(base.resolve()):
                raise ValueError("Trace path escapes campaign directory")
            viewer = trace_viewer(path, run["id"])
            parts.append(
                '<iframe title="Recorded Pi trajectory" sandbox="allow-scripts" '
                'style="width:100%;height:720px;border:1px solid #cddbd7" srcdoc="'
                + html.escape(viewer, quote=True)
                + '"></iframe>'
            )
        return "".join(parts)

    def validation(run):
        return (
            "<details><summary>Native validation · "
            + html.escape(run["id"])
            + "</summary><pre>"
            + html.escape(evidence(run["summary"]))
            + "</pre><details><summary>Harbor result</summary><pre>"
            + html.escape(evidence(run["result"]))
            + "</pre></details></details>"
        )

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
                "".join(authoring(run, stage) for run in stage.get("authoring_runs", []))
                or "<p>No generated task. Authoring and scientific validation remain pending.</p>"
            )
            + (
                "<h3>Acceptance and packaging record</h3><pre>"
                + html.escape(evidence(stage["acceptance"]))
                + "</pre>"
                if stage.get("acceptance")
                else ""
            )
            + "".join(validation(run) for run in stage.get("native_validations", []))
            + "</details><details><summary>Attempt</summary>"
            + (
                "".join(attempt(run) for run in stage["solver_attempts"])
                if stage.get("solver_attempts")
                else "<p>No solver attempt or score.</p>"
            )
            + "</details></article>"
        )
    output.write_text(
        '<!doctype html><html lang="en"><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<meta http-equiv="Content-Security-Policy" content="default-src &#39;none&#39;; '
        "style-src &#39;unsafe-inline&#39;; script-src &#39;unsafe-inline&#39;; "
        'frame-src &#39;self&#39; about:; connect-src &#39;none&#39;">'
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
