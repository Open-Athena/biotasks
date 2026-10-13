import json
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(
        executable_path="/home/exedev/.local/bin/chromium",
        headless=True,
        args=["--no-sandbox", "--disable-gpu", "--renderer-process-limit=1"],
    )
    page = browser.new_page()
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(
        sys.argv[1]
        if len(sys.argv) > 1
        else Path(__file__).with_name("index.html").resolve().as_uri()
    )
    page.get_by_role("button", name="Approaches", exact=True).click()
    for index in range(5):
        page.locator(".approach-flow button").nth(index).click()
        for select in page.locator(".approach-step-panel select").all():
            for option in range(select.locator("option").count()):
                select.select_option(str(option))
    page.get_by_role("button", name="Notebooks", exact=True).click()
    for tab in ["Notebook", "Task", "Attempt", "Review"]:
        page.get_by_role("button", name=tab, exact=True).click()
        assert page.locator(".panel h2").count() > 0
        if tab == "Attempt":
            select = page.locator(".panel select")
            for i in range(select.locator("option").count()):
                select.select_option(str(i))
    page.set_viewport_size({"width": 390, "height": 844})
    for tab in ["Notebook", "Task", "Attempt", "Review"]:
        page.get_by_role("button", name=tab, exact=True).click()
        assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
    page.get_by_role("button", name="Approaches", exact=True).click()
    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
    assert not errors, errors
    browser.close()
    print(
        json.dumps(
            {
                "tabs": 5,
                "all_selectors_checked": True,
                "mobile_overflow": False,
                "javascript_errors": errors,
            }
        )
    )
