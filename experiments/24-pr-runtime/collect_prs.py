"""Collect complete merged-PR metadata for the frozen panel and date window."""

import datetime
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent
FIELDS = (
    "number url title body mergedAt isDraft changedFiles "
    "baseRefOid headRefOid mergeCommit{oid} "
)


def request(repository, start, end, cursor=None):
    search = f"repo:{repository} is:pr is:merged merged:{start}..{end}"
    query = (
        "query{search(type:ISSUE,first:100,query:" + json.dumps(search)
        + (",after:" + json.dumps(cursor) if cursor else "")
        + "){issueCount pageInfo{hasNextPage endCursor} "
        + "nodes{... on PullRequest{" + FIELDS + "}}} rateLimit{remaining resetAt}}"
    )
    digest = hashlib.sha256(query.encode()).hexdigest()
    path = ROOT / "inventory/pr-pages" / f"{digest}.json"
    path.parent.mkdir(exist_ok=True)
    if path.exists():
        record = json.loads(path.read_text())
        if record["query_sha256"] != digest:
            raise ValueError("Query hash mismatch")
    else:
        result = subprocess.run(
            ["gh", "api", "graphql", "-f", f"query={query}"],
            capture_output=True, text=True, timeout=60, check=True,
        )
        response = json.loads(result.stdout)
        if response.get("errors") or not response.get("data"):
            raise RuntimeError(f"GraphQL errors: {response.get('errors')}")
        record = {
            "query_sha256": digest, "query": search, "cursor": cursor,
            "captured_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "response": response,
        }
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(record, indent=2) + "\n")
        tmp.replace(path)
    data = record["response"]["data"]
    if data["rateLimit"]["remaining"] < 100:
        raise RuntimeError("GraphQL budget below 100 points")
    return data["search"], str(path.relative_to(ROOT))


def window(repository, start, end):
    page, evidence = request(repository, start, end)
    if page["issueCount"] > 1000:
        first, last = datetime.date.fromisoformat(start), datetime.date.fromisoformat(end)
        if first == last:
            raise RuntimeError(f"More than 1000 PRs in one day for {repository}; cannot claim complete")
        middle = first + (last - first) // 2
        left, left_paths = window(repository, start, middle.isoformat())
        right, right_paths = window(repository, (middle + datetime.timedelta(days=1)).isoformat(), end)
        return left + right, [evidence] + left_paths + right_paths
    records = page["nodes"]
    paths = [evidence]
    expected = page["issueCount"]
    seen_cursors = set()
    while page["pageInfo"]["hasNextPage"]:
        cursor = page["pageInfo"]["endCursor"]
        if not cursor or cursor in seen_cursors:
            raise RuntimeError("Pagination cursor failed to advance")
        seen_cursors.add(cursor)
        page, evidence = request(repository, start, end, cursor)
        if page["issueCount"] != expected:
            raise RuntimeError("Search population changed during pagination; retain evidence and reassess")
        records.extend(page["nodes"])
        paths.append(evidence)
    if len(records) != expected or len({r["number"] for r in records}) != expected:
        raise ValueError(f"Incomplete or duplicate search results for {repository}")
    return records, paths


def main():
    panel = json.loads((ROOT / "inventory/repository-panel.json").read_text())
    results = []
    destination = ROOT / "inventory/pr-cohorts"
    destination.mkdir(exist_ok=True)
    for selected in panel["selected"]:
        repo = selected["repository"]
        rows, evidence = window(repo, panel["pr_window"]["since"], panel["pr_window"]["until"])
        for row in rows:
            if not row.get("mergedAt"):
                raise ValueError(f"Unmerged PR in merged query: {repo} {row['number']}")
        ranked = sorted(
            rows,
            key=lambda row: hashlib.sha256(
                f"biotasks-24-prs-v1:{selected['github_id']}:{row['number']}".encode()
            ).hexdigest(),
        )
        record = {
            "repository": repo, "stratum": selected["stratum"], "window": panel["pr_window"],
            "merged_pr_count": len(rows), "evidence": evidence,
            "sample_rule": "SHA256 rank of biotasks-24-prs-v1:github_id:number; first 20",
            "selected": ranked[:20],
        }
        (destination / (repo.replace("/", "__") + ".json")).write_text(json.dumps(record, indent=2) + "\n")
        results.append({
            "repository": repo, "stratum": selected["stratum"],
            "merged_pr_count": len(rows), "sampled": min(20, len(rows)),
        })
        print(json.dumps(results[-1]), flush=True)
    (ROOT / "inventory/pr-summary.json").write_text(json.dumps(results, indent=2) + "\n")


if __name__ == "__main__":
    main()
