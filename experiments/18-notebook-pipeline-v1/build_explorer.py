"""Build a read-only Notebook → Task → Attempt intake view; no external assets."""

import argparse
import html
import json
from pathlib import Path


def build(manifest, intake, output):
    seeds = json.loads(manifest.read_text())["seeds"]
    records = {r["id"]: r for r in json.loads(intake.read_text())["seeds"]}
    cards = []
    for seed in seeds:
        row = records[seed["id"]]
        e = html.escape
        source = intake.parent / seed["id"] / "seed.txt"
        text = source.read_text() if source.exists() else "Source unavailable; see intake status."
        cards.append(
            f'<article id="{e(seed["id"])}"><h2>{e(seed["domain"])} · {e(seed["label"])}</h2>'
            f'<p class="status">{e(row["status"])} · source inspection only</p>'
            "<details><summary>Notebook</summary>"
            f'<p><a href="{e(seed["url"], quote=True)}">Pinned source</a></p>'
            f"<p>{e(seed['focus'])}</p><p>{e(seed['input_origin'])}</p>"
            f"<pre>{e(text)}</pre></details>"
            "<details><summary>Task</summary><p>No generated task. Authoring, native reference "
            "validation, controls and acceptance remain pending.</p></details>"
            "<details><summary>Attempt</summary><p>No solver attempt, score or measured runtime."
            "</p></details></article>"
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
        "Intake preparation is not task generation or scientific validation. No model calls.</p>"
        + "".join(cards)
        + "</html>"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--intake", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    build(Path(__file__).with_name("seeds.json"), args.intake, args.output)
