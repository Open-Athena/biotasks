"""Exercise the offline page in one bounded Chromium instance (Playwright 1.56.0)."""

import argparse
import csv
import io
import json
import math
from collections import Counter
from pathlib import Path

from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent


def check_composition(page, depth=300, source_type=None, primary_group=None):
    """Compare rendered cells to independent sets built from the original CSVs."""
    baseline = HERE
    with (baseline / "source-annotations.csv").open() as handle:
        labels = {r["source_id"]: r for r in csv.DictReader(handle)}
    cohorts = {key: set() for key in ("bioconda", "bioconductor", "pypi", "github")}
    with (baseline / "rankings.csv").open() as handle:
        for row in csv.DictReader(handle):
            annotation = labels[row["source_id"]]
            if int(row["rank"]) > depth:
                continue
            if source_type and annotation["source_type"] != source_type:
                continue
            if primary_group and annotation["primary_domain"] != primary_group:
                continue
            cohorts[row["ranking"]].add(row["source_id"])
    cohorts["merged"] = set().union(*cohorts.values())
    mode = page.locator("#composition-mode").input_value()
    for container, field, attribute in (
        ("types", "source_type", "type"),
        ("coverage", "primary_domain", "domain"),
    ):
        counts = {
            key: Counter(labels[source][field] for source in ids) for key, ids in cohorts.items()
        }
        cells = page.locator(f"#{container}").evaluate(
            """(el, attr) => [...el.querySelectorAll('tbody tr')].map(row => ({
              category: row.querySelector('button').dataset[attr],
              cells: [...row.querySelectorAll('td')].map(cell => ({
                key: cell.dataset.cohort, count: Number(cell.dataset.count),
                total: Number(cell.dataset.total),
                share: cell.querySelector('.distribution-value span').textContent,
                width: parseFloat(cell.querySelector('.distribution-track span').style.width)
              }))
            }))""",
            attribute,
        )
        assert {row["category"] for row in cells} == set(counts["merged"])
        maximum = 1 if mode == "percent" else max(counts["merged"].values())
        for row in cells:
            assert [cell["key"] for cell in row["cells"]] == list(cohorts)
            for cell in row["cells"]:
                key = cell["key"]
                count, total = counts[key][row["category"]], len(cohorts[key])
                assert (cell["count"], cell["total"]) == (count, total)
                share = count / total if total else None
                if share is None:
                    assert cell["share"] == "—"
                else:
                    assert abs(float(cell["share"].rstrip("%")) - 100 * share) <= 0.050001
                expected_width = 100 * ((share or 0) if mode == "percent" else count) / maximum
                assert math.isclose(cell["width"], expected_width, abs_tol=0.0001)
        for key in cohorts:
            assert sum(
                cell["count"] for row in cells for cell in row["cells"] if cell["key"] == key
            ) == len(cohorts[key])


def exercise_composition(page, screenshots):
    page.locator('[data-tab="composition"]').click()
    assert page.locator("#filters").is_visible()
    assert "1,014 distinct" in page.locator("#composition-scope").inner_text()
    check_composition(page)
    page.screenshot(path=str(screenshots / "composition-desktop.png"), full_page=True)
    page.locator("#composition-mode").select_option("count")
    check_composition(page)
    page.locator("#depth").select_option("100")
    assert "335 distinct" in page.locator("#composition-scope").inner_text()
    check_composition(page, depth=100)
    page.locator("#composition-mode").select_option("percent")
    check_composition(page, depth=100)
    page.locator("#reset").click()
    page.locator('#types [data-type="Agent instructions"]').click()
    assert page.locator("#type").input_value() == "Agent instructions"
    check_composition(page, source_type="Agent instructions")
    assert "—" in page.locator("#types").inner_text()
    page.locator("#reset").click()
    page.locator('#coverage [data-domain="Immunology"]').click()
    check_composition(page, primary_group="Immunology")
    page.locator("#reset").click()
    page.locator("#search").fill("not-a-source-unique-test")
    assert page.locator("#composition .empty").count() == 2
    assert "NaN" not in page.locator("#composition").inner_text()
    page.locator("#reset").click()
    page.locator('[data-tab="explore"]').click()


def exercise_tail(page, screenshots):
    with (HERE / "primary-group-depths.csv").open() as f:
        expected = {
            (r["cohort"], int(r["depth"]), r["primary_group"]): r for r in csv.DictReader(f)
        }
    with (HERE / "rank-correlations.csv").open() as f:
        pair_rows = list(csv.DictReader(f))
    # All 18 intersections and correlations, including original cutoff prefixes.
    for r in pair_rows:
        actual = page.evaluate(
            "r=>{const e=DiscoveryExplorer;const p=e.pairStats(e.data.sources,r.first,r.second,Number(r.depth));return {n:p.shared.length,j:p.jaccard,rho:p.rho}}",
            r,
        )
        assert actual["n"] == int(r["n_shared"])
        assert math.isclose(actual["j"], float(r["jaccard"]), abs_tol=1e-12)
        assert (
            actual["rho"] is None
            if not r["spearman_rho"]
            else math.isclose(actual["rho"], float(r["spearman_rho"]), abs_tol=1e-12)
        )
    page.locator('[data-tab="tail"]').click()
    assert not page.locator("#filters").is_visible()
    for cohort in ["bioconda", "bioconductor", "pypi", "github", "merged"]:
        page.locator("#tail-cohort").select_option(cohort)
        for focus in ["sparse100", "fixed", "new", "current", "all"]:
            page.locator("#tail-focus").select_option(focus)
            initial = {
                g: int(r["count"]) for (m, k, g), r in expected.items() if m == cohort and k == 100
            }
            last = {
                g: int(r["count"]) for (m, k, g), r in expected.items() if m == cohort and k == 300
            }
            chosen = {
                g
                for g, n in initial.items()
                if focus == "all"
                or (focus == "sparse100" and n <= 5)
                or (focus == "fixed" and 1 <= n <= 5)
                or (focus == "new" and n == 0)
                or (focus == "current" and 1 <= last[g] <= 5)
            }
            for scale in ["count", "share"]:
                page.locator("#tail-scale").select_option(scale)
                cells = page.locator("#tail-detail tbody tr[data-group]").evaluate_all(
                    "rows=>rows.map(row=>({group:row.dataset.group,cells:[...row.querySelectorAll('td[data-depth]')].map(c=>({depth:Number(c.dataset.depth),count:Number(c.dataset.count),total:Number(c.dataset.total),share:c.querySelector('.distribution-value span').textContent,width:parseFloat(c.querySelector('.distribution-track span').style.width)}))}))"
                )
                assert {r["group"] for r in cells} == chosen
                maximum = max(
                    [1e-12]
                    + [
                        float(expected[cohort, k, g]["share" if scale == "share" else "count"])
                        for g in chosen
                        for k in [100, 200, 300]
                    ]
                )
                for row in cells:
                    for cell in row["cells"]:
                        r = expected[cohort, cell["depth"], row["group"]]
                        assert (cell["count"], cell["total"]) == (int(r["count"]), int(r["total"]))
                        assert (
                            abs(float(cell["share"].rstrip("%")) - 100 * float(r["share"]))
                            <= 0.050001
                        )
                        assert math.isclose(
                            cell["width"],
                            100 * float(r["share" if scale == "share" else "count"]) / maximum,
                            abs_tol=0.0001,
                        )
        # Compare count bands including absent groups with independent CSV rows.
        actual = page.evaluate("m=>DiscoveryExplorer.tailData(m)", cohort)
        for d in actual:
            bands = Counter(
                r["band"] for (m, k, g), r in expected.items() if m == cohort and k == d["k"]
            )
            assert all(d["bands"][b] == bands[b] for b in d["bands"])
            assert sum(d["bands"].values()) == 22
    page.locator("#tail-focus").select_option("sparse100")
    page.locator("#tail-scale").select_option("count")
    page.screenshot(path=str(screenshots / "tail-desktop.png"), full_page=True)
    page.locator("#tail-scale").select_option("share")
    page.screenshot(path=str(screenshots / "tail-share-desktop.png"), full_page=True)
    page.locator('[data-tail-group="RNA structure"]').click()
    assert page.locator("#domain").input_value() == "RNA structure"
    assert page.evaluate("DiscoveryExplorer.tableRows().length") == 3
    page.locator("#reset").click()
    page.locator('[data-tab="explore"]').click()


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
            assert "1,014" in page.locator("#filter-status").inner_text()
            exercise_composition(page, args.screenshots)
            exercise_tail(page, args.screenshots)
            comparison = page.evaluate("""() => {
                const e=window.DiscoveryExplorer;
                return {pairs:e.data.depthResults.pairs.filter(p=>p.depth===300).map(p=>({expected:p,actual:e.pairStats(e.data.sources,p.first,p.second,300)})),
                  adoption:e.data.adoptionPairs.map(p=>({expected:p,actual:e.adoptionStats(p.first,p.second)})),
                  depths:e.depthData(), tied:e.spearman([1,1,2,3],[3,3,2,1])};
            }""")
            for pair in comparison["pairs"]:
                expected, actual = pair["expected"], pair["actual"]
                assert len(actual["shared"]) == expected["n_shared"]
                assert math.isclose(actual["jaccard"], expected["jaccard"], abs_tol=1e-12)
                rho = expected["spearman_rho"]
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
            assert comparison["depths"][-1] == {"k": 300, "n": 1014, "topics": 157, "domains": 22}
            for method in ("bioconda", "bioconductor", "pypi", "github"):
                page.locator(f'[data-sort="{method}"]').click()
                for _ in range(2):
                    result = page.evaluate(
                        """m=>{const e=window.DiscoveryExplorer;return {direction:e.state.direction,values:e.tableRows().map(r=>r.ranks[m]?.rank??null)}}""",
                        method,
                    )
                    values = result["values"]
                    assert all(v is None for v in values[300:])
                    assert values[:300] == sorted(range(1, 301), reverse=result["direction"] < 0)
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
            assert len(exported) == 1014 and len({r["source_id"] for r in exported}) == 1014
            assert any(r["bioconda_rank"] == "" for r in exported)
            page.screenshot(path=str(args.screenshots / "explorer-desktop.png"))
            page.locator('[data-tab="compare"]').click()
            page.locator('[data-overlap="bioconda,bioconductor"]').click()
            assert page.evaluate("DiscoveryExplorer.tableRows().length") == 73
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
            page.locator('[data-tab="composition"]').click()
            assert page.evaluate("document.documentElement.scrollWidth<=window.innerWidth")
            assert page.locator("#types").evaluate("el=>el.scrollWidth>el.clientWidth")
            page.locator("#types").evaluate("el=>el.scrollLeft=el.scrollWidth")
            page.screenshot(path=str(args.screenshots / "composition-mobile.png"), full_page=True)
            page.locator('[data-tab="tail"]').click()
            assert page.evaluate("document.documentElement.scrollWidth<=window.innerWidth")
            page.screenshot(path=str(args.screenshots / "tail-mobile.png"), full_page=True)
            assert not errors, errors
            if args.url.startswith("file:"):
                assert not [url for url in requests if url.startswith(("https:", "http:"))]
            print(
                json.dumps(
                    {
                        "result": "PASS",
                        "url": args.url,
                        "offline": args.url.startswith("file:"),
                        "chromium": browser.version,
                        "sources": 1014,
                        "ranking_pairs": 18,
                        "adoption_pairs": 6,
                        "numeric_tolerance": 1e-12,
                        "desktop": [1440, 1080],
                        "mobile": [390, 844],
                        "page_errors": errors,
                        "network_requests": len(requests),
                        "checks": [
                            "type and primary-group distributions against independent CSV joins",
                            "all tail cells, shares, count bands, cohort/focus/scale controls and drilldown",
                            "deduplicated union, top-100 depth, filters, zero and empty populations",
                            "count and percentage bar scales and denominators",
                            "exact saved correlations and counts",
                            "ties and missing values",
                            "all four rank sorts in both directions, nulls last",
                            "search and empty state",
                            "source details and Escape",
                            "top-100 union",
                            "scientific type and domain filters",
                            "1014-row CSV download",
                            "overlap and exact-membership drilldown",
                            "empty correlation pairs",
                            "mobile horizontal overflow",
                        ]
                        + (["offline operation"] if args.url.startswith("file:") else []),
                    }
                )
            )
        finally:
            browser.close()


if __name__ == "__main__":
    main()
