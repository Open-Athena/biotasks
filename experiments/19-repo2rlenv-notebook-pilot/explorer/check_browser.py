"""Check the current standalone explorer's routes, documents and mobile layout."""

import argparse
import json
from pathlib import Path

from playwright.sync_api import sync_playwright

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--index", type=Path, default=Path(__file__).with_name("index.html"))
args = parser.parse_args()
index = args.index.resolve()
manifest = json.loads(index.with_name("source-manifest.json").read_text())

with sync_playwright() as p:
    browser = p.chromium.launch(
        executable_path="/home/exedev/.local/bin/chromium",
        headless=True,
        # This static viewer needs no software GPU process on the shared VM.
        args=[
            "--no-sandbox",
            "--disable-gpu",
            "--renderer-process-limit=1",
            "--no-zygote",
            "--disable-software-rasterizer",
        ],
    )
    page = browser.new_page()
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.goto(index.as_uri())
    for label, key in [
        ("Notebook", "notebook"),
        ("Task", "task"),
        ("Attempt", "attempt"),
        ("Pipeline", "pipeline"),
        ("Validation", "review"),
    ]:
        page.get_by_role("link", name=label, exact=True).click()
        page.locator("#" + key).wait_for(state="visible")
    page.get_by_role("link", name="Pipeline", exact=True).click()
    assert page.locator(".stage-nav a").count() == len(manifest["stage_ids"])
    for anchor in page.locator(".stage-nav a").all():
        anchor.click()
        assert page.locator(anchor.get_attribute("href")).is_visible()
    page.get_by_role("link", name="Attempt", exact=True).click()
    # The selected input trajectory defines the count; it is not a fixture's
    # reward, turn count or mutable publication status.
    expected_details = manifest["solver_steps"] + (2 if manifest["has_solver_trajectory"] else 0)
    assert page.locator("#attempt details").count() == expected_details
    if manifest["solver_steps"]:
        for detail in page.locator("#attempt > details").all():
            detail.locator("summary").first.click()
        if manifest["solver_tool_steps"]:
            assert page.get_by_role("heading", name="Tool calls", exact=True).first.is_visible()
    page.set_viewport_size({"width": 390, "height": 844})
    for label in ["Notebook", "Task", "Attempt", "Pipeline", "Validation"]:
        page.get_by_role("link", name=label, exact=True).click()
        assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth"), label
    assert not errors, errors
    browser.close()
    print(
        json.dumps(
            {
                "views": 5,
                "stages": len(manifest["stage_ids"]),
                "mobile_overflow": False,
                "javascript_errors": errors,
            }
        )
    )
