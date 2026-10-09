"""Summarize recorded outcomes without treating pending seeds as failures."""

import argparse
import hashlib
import json
from pathlib import Path


def summarize(campaign_path):
    base = campaign_path.parent
    campaign = json.loads(campaign_path.read_text())
    rows = []
    for seed in campaign["seeds"]:
        authors = []
        for run in seed["authoring_runs"]:
            result = json.loads((base / run["result"]).read_text())
            requests = result.get("requests", [])
            usage = [r["usage"] for r in requests if r.get("usage")]
            authors.append(
                {
                    "id": run["id"],
                    "outcome": result.get("outcome", "see preserved review"),
                    "seconds": result.get("elapsed_seconds"),
                    "requests": len(requests),
                    "requests_with_usage": len(usage),
                    "input_tokens_including_cache_recorded": sum(
                        u.get("prompt_tokens", 0) for u in usage
                    ),
                    "output_tokens_recorded": sum(u.get("completion_tokens", 0) for u in usage),
                    "usage_complete": bool(requests) and len(usage) == len(requests),
                    "evidence": run["result"],
                }
            )
        attempts = [
            {
                "id": run["id"],
                "evidence": run["summary"],
                **json.loads((base / run["summary"]).read_text()),
            }
            for run in seed["solver_attempts"]
        ]
        rows.append(
            {
                "id": seed["id"],
                "status": seed["status"],
                "accepted": seed["accepted"],
                "authoring": authors,
                "native_validations": [
                    {
                        "id": run["id"],
                        "evidence": run["summary"],
                        **json.loads((base / run["summary"]).read_text()),
                    }
                    for run in seed.get("native_validations", [])
                ],
                "solver_attempts": attempts,
            }
        )
    sessions = [run for row in rows for run in row["authoring"]]
    attempts = [run for row in rows for run in row["solver_attempts"]]
    return {
        "campaign_sha256": hashlib.sha256(campaign_path.read_bytes()).hexdigest(),
        "campaign_complete": campaign["complete"],
        "scope": "Initial purposive panel only; not a representative benchmark estimate",
        "original_seed_count": len(rows),
        "seeds_with_completed_authoring_records": sum(bool(r["authoring"]) for r in rows),
        "accepted_tasks": sum(row["accepted"] for row in rows),
        "accepted_fraction_of_original_panel": sum(r["accepted"] for r in rows) / len(rows),
        "completed_authoring_sessions": len(sessions),
        "authoring_seconds_recorded": sum(r["seconds"] or 0 for r in sessions),
        "authoring_sessions_missing_time": sum(r["seconds"] is None for r in sessions),
        "authoring_requests_recorded": sum(r["requests"] for r in sessions),
        "authoring_requests_with_usage": sum(r["requests_with_usage"] for r in sessions),
        "biological_solver_attempts_recorded": len(attempts),
        "full_biological_successes": sum(r.get("full_success") is True for r in attempts),
        "cost": {
            "inference_service": "existing free GLM service",
            "orchestration_usd": None,
            "meaning": "Unmeasured orchestration cost is not zero total cost",
        },
        "limits": [
            "Pending seeds remain in the original-panel denominator",
            "Author exit status alone does not determine candidate acceptance",
            "Recorded token subtotals are incomplete where usage is missing",
            "Technical integration trials are excluded from biological solver counts",
        ],
        "seeds": rows,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--campaign", type=Path, default=Path(__file__).with_name("campaign.json"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.write_text(json.dumps(summarize(args.campaign), indent=2) + "\n")
