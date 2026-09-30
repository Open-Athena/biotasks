"""Extend the frozen candidate screen; no refreshed ranking metrics."""

import argparse
import csv
import datetime
import hashlib
import heapq
import json
import re
import subprocess
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
STUDY = HERE.parent.parent
CACHE = Path("/tmp/bio-discovery-20260929")
RECIPE_REV = "254ba2d4bcda7fe6ed2baa586bac6c35885a4b10"
IMPORTS = [
    "top200/cohorts-provisional.json",
    "top200/identity-overrides.json",
    "top200/screening-decisions.json",
    "top200/github-source-metadata.json",
    "bioconda-packages.tsv",
    "bioconductor-scores.tsv",
    "bioconductor-metadata.json",
    "top200/pypi-counts-without-mirrors.json",
]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dump(name, data):
    (HERE / name).write_text(json.dumps(data, indent=2) + "\n")


def imports():
    manifest = json.loads((STUDY / "runs/2026-09-30-migration/retained-cache.json").read_text())
    by_path = {r["path"]: r for r in manifest["files"]}
    checked = []
    for rel in IMPORTS:
        path = CACHE / rel
        actual = sha(path)
        archive_path = str(path.resolve().relative_to(CACHE))
        assert actual == by_path[archive_path]["sha256"], (rel, archive_path)
        checked.append(
            {
                "path": rel,
                "archive_path": archive_path,
                "bytes": path.stat().st_size,
                "sha256": actual,
            }
        )
    dump(
        "imported-inputs.json",
        {
            "archive_manifest": "../2026-09-30-bucket-archive/manifest.json",
            "verified_files": checked,
        },
    )


def largest_tsv(name, score, count):
    with (CACHE / name).open() as f:
        return heapq.nlargest(count, csv.DictReader(f, delimiter="\t"), key=lambda r: int(r[score]))


def fetch(url, limit=12_000_000):
    req = urllib.request.Request(url, headers={"User-Agent": "BioTasks-source-discovery/1.0"})
    with urllib.request.urlopen(req, timeout=30) as response:
        payload = response.read(limit + 1)
    assert len(payload) <= limit
    return payload


def collect():
    imports()
    folder = HERE / "metadata"
    folder.mkdir(exist_ok=True)
    rows = largest_tsv("bioconda-packages.tsv", "total", 550)
    records = []
    for i, row in enumerate(rows[500:], 501):
        name = row["package"]
        record = {"package": name, "raw_rank": i, "score": int(row["total"])}
        if (name.startswith("perl-") and not name.startswith("perl-bio")) or name in {
            "tidyp",
            "parallel",
        }:
            record["exclusion"] = (
                "General-purpose computing dependency; no biology-specific functionality in package scope."
            )
        elif name.startswith("bioconductor-"):
            record["bioconductor_hint"] = name.removeprefix("bioconductor-")
        else:
            url = f"https://raw.githubusercontent.com/bioconda/bioconda-recipes/{RECIPE_REV}/recipes/{name}/meta.yaml"
            path = folder / f"recipe-{name}.json"
            if path.exists():
                record.update(json.loads(path.read_text()))
            else:
                try:
                    raw = fetch(url, 1_000_000)
                    content = raw.decode()
                    variables = dict(re.findall(r'{% set (\w+) = ["\']([^"\']+)["\'] %}', content))
                    fields = {
                        key: value.strip("\"'")
                        for key, value in re.findall(
                            r"^  (home|dev_url|doc_url|summary|license):\s*(.+)$", content, re.M
                        )
                    }
                    for key in fields:
                        for var, value in variables.items():
                            fields[key] = fields[key].replace("{{ " + var + " }}", value)
                    record.update(fields)
                    record.update(
                        {
                            "recipe_url": url,
                            "recipe_sha256": hashlib.sha256(raw).hexdigest(),
                            "github_links": list(
                                dict.fromkeys(
                                    re.findall(r"https?://github.com/([\w.-]+/[\w.-]+)", content)
                                )
                            ),
                            "observed_at": datetime.datetime.now(datetime.UTC).isoformat(),
                        }
                    )
                except urllib.error.HTTPError as e:
                    record["error_status"] = e.code
                    record["recipe_url"] = url
                path.write_text(json.dumps(record, indent=2) + "\n")
        records.append(record)
    dump("additional-bioconda.json", records)
    pypi = json.loads((CACHE / "top200/pypi-counts-without-mirrors.json").read_text())["data"]
    for i, row in enumerate(pypi[350:400], 351):
        name = row["project"]
        path = folder / f"pypi-{name}.json"
        if path.exists():
            continue
        url = f"https://pypi.org/pypi/{name}/json"
        try:
            raw = fetch(url)
            payload = json.loads(raw)
            info = payload["info"]
            record = {
                "package": name,
                "raw_rank": i,
                "score": int(row["downloads_30d"]),
                "source_url": url,
                "observed_at": datetime.datetime.now(datetime.UTC).isoformat(),
                "response_sha256": hashlib.sha256(raw).hexdigest(),
                "metadata": {
                    key: info.get(key)
                    for key in [
                        "name",
                        "version",
                        "summary",
                        "home_page",
                        "project_urls",
                        "classifiers",
                        "keywords",
                    ]
                },
                "source_distributions": [
                    {"url": r["url"], "sha256": r["digests"]["sha256"]}
                    for r in payload["urls"]
                    if r["packagetype"] == "sdist"
                ],
            }
        except urllib.error.HTTPError as e:
            record = {"package": name, "error_status": e.code, "source_url": url}
        path.write_text(json.dumps(record, indent=2) + "\n")
        if i % 10 == 0:
            print("PyPI identities", i, flush=True)
    print("Collected metadata beyond the archived screen", flush=True)


def github_names(text):
    return list(
        dict.fromkeys(
            s.lower().removesuffix(".git").rstrip(".")
            for s in re.findall(r"https?://(?:www\.)?github.com/([\w.-]+/[\w.-]+)", text or "")
        )
    )


def assemble():
    imports()
    original = json.loads((CACHE / "top200/cohorts-provisional.json").read_text())
    records = original["all_records"]
    baseline = {
        r["source_id"]: r
        for r in json.loads(
            (
                STUDY / "baseline/data/top200-2026-09-29/source-observations-2026-09-29.json"
            ).read_text()
        )
    }
    # Preserve the final corrected exported source records for every baseline source.
    for key, source in baseline.items():
        if key in records:
            records[key].update({k: v for k, v in source.items() if k != "observations"})
    bio = json.loads((CACHE / "bioconductor-metadata.json").read_text())
    bio_names = {name.lower(): name for name in bio}
    gh = json.loads((CACHE / "top200/github-source-metadata.json").read_text())["records"]
    additional = HERE / "github-identities.json"
    if additional.exists():
        gh += json.loads(additional.read_text())["records"]
    aliases = {
        r["requested_name"].lower(): r["metadata"]["nameWithOwner"].lower()
        for r in gh
        if r["metadata"]
    }
    metadata = {r["metadata"]["nameWithOwner"].lower(): r["metadata"] for r in gh if r["metadata"]}
    decisions = (
        json.loads((HERE / "decisions.json").read_text())
        if (HERE / "decisions.json").exists()
        else {"exclude": {}, "identity": {}}
    )

    def canonical(url):
        names = github_names(url)
        if names:
            key = aliases.get(names[0], names[0])
            return "github:" + key, metadata[key][
                "url"
            ] if key in metadata else "https://github.com/" + key
        if "git.bioconductor.org/packages/" in url:
            return "bioconductor:" + url.rsplit("/", 1)[1].lower(), url
        return url.lower().rstrip("/"), url

    def insert(name, url, summary, route, package, score, rank, evidence, details=None):
        url = decisions["identity"].get(route + ":" + package, url)
        key, url = canonical(url)
        if key not in records:
            records[key] = {
                "source_id": key,
                "name": name,
                "source_url": url,
                "summary": summary or "",
                "github": metadata.get(key.removeprefix("github:"))
                if key.startswith("github:")
                else None,
                "evidence_urls": [],
                "observations": [],
            }
        if evidence not in records[key]["evidence_urls"]:
            records[key]["evidence_urls"].append(evidence)
        if not any(
            o["route"] == route and o["package"] == package for o in records[key]["observations"]
        ):
            records[key]["observations"].append(
                {
                    "route": route,
                    "package": package,
                    "score": score,
                    "raw_rank": rank,
                    **(details or {}),
                }
            )

    def bio_source(name):
        data = bio.get(name, {})
        names = github_names(" ".join(data.get(k, "") for k in ["BugReports", "URL"]))
        return (
            "https://github.com/" + names[0]
            if names
            else "https://git.bioconductor.org/packages/" + name
        )

    for rank, row in enumerate(largest_tsv("bioconductor-scores.tsv", "Download_score", 350), 1):
        if rank <= 250:
            continue
        name = row["Package"]
        entry = bio.get(name, {})
        insert(
            name,
            bio_source(name),
            entry.get("Title", ""),
            "bioconductor",
            name,
            int(row["Download_score"]),
            rank,
            f"https://bioconductor.org/packages/3.23/bioc/html/{name}.html",
            {"description": entry.get("Description", ""), "biocViews": entry.get("biocViews", "")},
        )
    package_sources = {
        o["package"]: key
        for key, r in records.items()
        for o in r["observations"]
        if o["route"] == "bioconda"
    }
    for row in json.loads((HERE / "additional-bioconda.json").read_text()):
        name = row["package"]
        if row.get("exclusion") or row.get("error_status"):
            continue
        if name in package_sources:
            url = records[package_sources[name]]["source_url"]
        elif row.get("bioconductor_hint"):
            url = bio_source(bio_names.get(row["bioconductor_hint"], row["bioconductor_hint"]))
        else:
            url = row.get("dev_url") or row.get("home") or ""
            names = github_names(url) or [
                s.lower() for s in row.get("github_links", []) if not s.startswith("bioconda/")
            ]
            if names:
                url = "https://github.com/" + names[0]
        insert(
            name,
            url,
            row.get("summary", ""),
            "bioconda",
            name,
            row["score"],
            row["raw_rank"],
            row.get("recipe_url", ""),
            {},
        )
    for path in sorted((HERE / "metadata").glob("pypi-*.json")):
        row = json.loads(path.read_text())
        if row.get("error_status"):
            continue
        info, name = row["metadata"], row["package"]
        urls = info.get("project_urls") or {}
        preferred = sorted(
            urls.items(),
            key=lambda kv: (
                0
                if "repository" in kv[0].lower()
                or ("source" in kv[0].lower() and "documentation" not in kv[0].lower())
                else 1
                if "home" in kv[0].lower()
                else 2
            ),
        )
        names = github_names(" ".join(v for k, v in preferred))
        url = (
            "https://github.com/" + names[0]
            if names
            else info.get("home_page") or next(iter(urls.values()), "")
        )
        if not url or not url.startswith("http"):
            url = (
                row["source_distributions"][0]["url"]
                if row["source_distributions"]
                else f"https://pypi.org/project/{name}/"
            )
        insert(
            name,
            url,
            info.get("summary"),
            "pypi",
            name,
            row["score"],
            row["raw_rank"],
            row["source_url"],
        )
    cohorts = {}
    for route in ["bioconda", "bioconductor", "pypi", "github"]:
        candidates = []
        for key, record in records.items():
            obs = [
                o
                for o in record["observations"]
                if o["route"] == route
                and route + ":" + o["package"] not in decisions["exclude"]
                and key not in decisions["exclude"]
            ]
            if obs:
                candidates.append(
                    {
                        "source_id": key,
                        "score": max(o["score"] for o in obs),
                        "packages": [o["package"] for o in obs],
                        "first_raw_rank": min(o["raw_rank"] for o in obs),
                    }
                )
        leaders = heapq.nsmallest(300, candidates, key=lambda r: (-r["score"], r["source_id"]))
        assert len(leaders) == 300, (route, len(candidates))
        assert [(r["source_id"], r["score"]) for r in leaders[:200]] == [
            (r["source_id"], r["score"]) for r in original["cohorts"][route]
        ], route
        cohorts[route] = [{"rank": i, **r} for i, r in enumerate(leaders, 1)]
        print(
            route,
            len(candidates),
            "cutoff",
            leaders[-1]["score"],
            "raw rank",
            leaders[-1]["first_raw_rank"],
        )
    selected = {r["source_id"] for rows in cohorts.values() for r in rows}
    dump(
        "provisional.json",
        {
            "checkpoint": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
            "cohorts": cohorts,
            "sources": [records[key] for key in sorted(selected)],
            "all_records": records,
        },
    )
    print("union", len(selected), "new to baseline", len(selected - set(baseline)))
    with (HERE / "review.tsv").open("w") as f:
        w = csv.writer(f, delimiter="\t")
        w.writerow(["source_id", "name", "routes", "summary", "evidence"])
        for key in sorted(selected - set(baseline)):
            record = records[key]
            w.writerow(
                [
                    key,
                    record["name"],
                    ",".join(
                        route
                        for route in cohorts
                        if any(r["source_id"] == key for r in cohorts[route])
                    ),
                    record["summary"],
                    ";".join(record["evidence_urls"]),
                ]
            )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["collect", "assemble"])
    args = parser.parse_args()
    collect() if args.action == "collect" else assemble()
