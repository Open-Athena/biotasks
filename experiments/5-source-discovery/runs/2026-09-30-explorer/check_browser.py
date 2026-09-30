"""Exercise the offline page in one bounded Chromium instance (Playwright 1.56.0)."""

import argparse
import csv
import io
import json
import math
from pathlib import Path

from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--screenshots", type=Path, required=True)
    parser.add_argument("--url", default=(HERE / "explorer.html").as_uri())
    args = parser.parse_args()
    args.screenshots.mkdir(parents=True, exist_ok=True)
    errors, requests = [], []
    with sync_playwright() as driver:
        browser = driver.chromium.launch(
            executable_path="/home/exedev/.local/bin/chromium",
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
                "--no-zygote",
                "--disable-gpu-compositing",
                "--disable-software-rasterizer",
                "--use-gl=disabled",
                "--renderer-process-limit=1",
                "--disable-extensions",
            ],
        )
        try:
            context = browser.new_context(
                viewport={"width": 1440, "height": 1080}, accept_downloads=True
            )
            if args.url.startswith("file:"):
                context.set_offline(True)
            page = context.new_page()
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.on("request", lambda request: requests.append(request.url))
            page.goto(args.url, wait_until="load", timeout=40000)
            page.wait_for_function("window.DiscoveryExplorer !== undefined", timeout=30000)
            assert page.locator("#source-rows tr").count() == 25
            assert "672" in page.locator("#filter-status").inner_text()
            comparison = page.evaluate("""() => {
                const e=window.DiscoveryExplorer;
                return {pairs:e.data.baselinePairs.map(p=>({expected:p,actual:e.pairStats(e.data.sources,p.first,p.second,200)})),
                  adoption:e.data.adoptionPairs.map(p=>({expected:p,actual:e.adoptionStats(p.first,p.second)})),
                  depths:e.depthData(), tied:e.spearman([1,1,2,3],[3,3,2,1])};
            }""")
            for pair in comparison["pairs"]:
                expected, actual = pair["expected"], pair["actual"]
                assert len(actual["shared"]) == expected["intersection"]
                assert math.isclose(actual["jaccard"], expected["jaccard"], abs_tol=1e-12)
                rho = expected["spearman_within_intersection"]
                assert (
                    actual["rho"] is None
                    if rho is None
                    else math.isclose(actual["rho"], rho, abs_tol=1e-12)
                )
            for pair in comparison["adoption"]:
                expected, actual = pair["expected"], pair["actual"]
                assert len(actual["rows"]) == expected["n"]
                rho = expected["rho"]
                assert (
                    actual["rho"] is None
                    if rho is None
                    else math.isclose(actual["rho"], rho, abs_tol=1e-12)
                )
            assert comparison["tied"] == -1
            assert next(p for p in comparison["depths"] if p["k"] == 100)["n"] == 335
            assert comparison["depths"][-1] == {"k": 200, "n": 672, "topics": 125, "domains": 22}
            for method in ("bioconda", "bioconductor", "pypi", "github"):
                page.locator(f'[data-sort="{method}"]').click()
                for _ in range(2):
                    result = page.evaluate(
                        """m=>{const e=window.DiscoveryExplorer;return {direction:e.state.direction,values:e.tableRows().map(r=>r.ranks[m]?.rank??null)}}""",
                        method,
                    )
                    values = result["values"]
                    assert all(v is None for v in values[200:])
                    assert values[:200] == sorted(range(1, 201), reverse=result["direction"] < 0)
                    page.locator(f'[data-sort="{method}"]').click()
            page.locator("#search").fill("pysam")
            assert page.evaluate(
                'DiscoveryExplorer.tableRows().some(r=>r.id==="github:pysam-developers/pysam")'
            )
            page.locator(".source-name").first.click()
            assert page.locator("#source-dialog").is_visible()
            page.keyboard.press("Escape")
            page.locator("#search").fill("not-a-source-unique-test")
            assert "No sources match" in page.locator("#source-rows").inner_text()
            page.locator("#reset").click()
            page.locator("#depth").select_option("100")
            assert page.evaluate("DiscoveryExplorer.tableRows().length") == 335
            page.locator("#reset").click()
            page.locator("#scientific").check()
            assert page.evaluate(
                'DiscoveryExplorer.tableRows().every(r=>["Software","Workflow","Research implementation"].includes(r.type))'
            )
            page.locator("#reset").click()
            page.locator("#domain").select_option("Immunology")
            assert page.evaluate('DiscoveryExplorer.tableRows().every(r=>r.domain==="Immunology")')
            page.locator("#reset").click()
            with page.expect_download() as download:
                page.locator("#export").click()
            exported = list(csv.DictReader(io.StringIO(Path(download.value.path()).read_text())))
            assert len(exported) == 672 and len({r["source_id"] for r in exported}) == 672
            assert any(r["bioconda_rank"] == "" for r in exported)
            page.screenshot(path=str(args.screenshots / "explorer-desktop.png"))
            page.locator('[data-tab="compare"]').click()
            page.locator('[data-overlap="bioconda,bioconductor"]').click()
            assert page.evaluate("DiscoveryExplorer.tableRows().length") == 54
            page.locator("#clear-membership").click()
            page.locator('[data-tab="compare"]').click()
            first = page.locator("[data-mask]").first
            count = int(first.locator(".intersection-value").inner_text())
            first.click()
            assert page.evaluate("DiscoveryExplorer.tableRows().length") == count
            page.locator("#clear-membership").click()
            page.locator('[data-tab="compare"]').click()
            page.locator("#rank-pair").select_option("3")
            assert "0 shared sources" in page.locator("#rank-summary").inner_text()
            page.locator("#rank-pair").select_option("0")
            page.screenshot(path=str(args.screenshots / "comparison-desktop.png"), full_page=True)
            page.locator("#search").fill("not-a-source-unique-test")
            assert "0 filtered sources" in page.locator("#comparison-scope").inner_text()
            page.locator("#reset").click()
            page.locator('[data-tab="adoption"]').click()
            assert "82 complete pairs" in page.locator("#adoption-summary").inner_text()
            page.locator("#adoption-pair").select_option("3")
            assert "0 complete pairs" in page.locator("#adoption-summary").inner_text()
            page.locator("#adoption-pair").select_option("2")
            page.locator('[data-tab="methods"]').click()
            assert page.locator("#method-definitions dl").count() == 1
            page.locator('[data-tab="explore"]').click()
            page.set_viewport_size({"width": 390, "height": 844})
            assert page.evaluate("document.documentElement.scrollWidth<=window.innerWidth")
            page.screenshot(path=str(args.screenshots / "explorer-mobile.png"), full_page=True)
            page.locator('[data-tab="compare"]').click()
            assert page.evaluate("document.documentElement.scrollWidth<=window.innerWidth")
            assert not errors, errors
            if args.url.startswith("file:"):
                assert not [url for url in requests if url.startswith(("https:", "http:"))]
            print(
                json.dumps(
                    {
                        "result": "PASS",
                        "chromium": browser.version,
                        "sources": 672,
                        "ranking_pairs": 6,
                        "adoption_pairs": 6,
                        "numeric_tolerance": 1e-12,
                        "desktop": [1440, 1080],
                        "mobile": [390, 844],
                        "page_errors": errors,
                        "network_requests": len(requests),
                        "checks": [
                            "exact saved correlations and counts",
                            "ties and missing values",
                            "all four rank sorts in both directions, nulls last",
                            "search and empty state",
                            "source details and Escape",
                            "top-100 union",
                            "scientific type and domain filters",
                            "672-row CSV download",
                            "overlap and exact-membership drilldown",
                            "empty correlation pairs",
                            "mobile horizontal overflow",
                            "offline operation",
                        ],
                    }
                )
            )
        finally:
            browser.close()


if __name__ == "__main__":
    main()
