"""Summarize recovered ZCode telemetry without exporting prompts or tool content.

This is operational evidence, not scientific task review. Input is an observation
directory containing one directory per item, with early/final text exports.
"""

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path


def digest(path: Path) -> str:
    with path.open("rb") as source:
        return hashlib.file_digest(source, "sha256").hexdigest()


def summarize(item: Path) -> dict:
    export = item / "final"
    if not (export / "zcode-events.jsonl").is_file():
        export = item / "early"
    events_path = export / "zcode-events.jsonl"
    result_path = export / "result.json"
    result = json.loads(result_path.read_text())
    requests = result["requests"]
    sources: Counter = Counter()
    tools: Counter = Counter()
    finishes: Counter = Counter()
    usage: Counter = Counter()
    commands: Counter = Counter()
    wrapper_failures = 0
    scheduled = set()
    completed = set()
    with events_path.open() as events:
        for line in events:
            event = json.loads(line)
            payload = event.get("payload", {})
            if (
                event["type"] == "session.updated"
                and payload.get("type") == "model_request_completed"
            ):
                request_id = payload["requestId"]
                if request_id in completed:
                    raise ValueError("Duplicate completed request event")
                completed.add(request_id)
                sources[payload.get("querySource", "unknown")] += 1
                finishes[payload.get("finishReason", "unknown")] += 1
                for key, value in payload.get("usage", {}).items():
                    if isinstance(value, (int, float)):
                        usage[key] += value
            if event["type"] != "tool.updated":
                continue
            if payload.get("kind") == "scheduled":
                call_id = payload["toolCallId"]
                if call_id in scheduled:
                    raise ValueError("Duplicate scheduled tool event")
                scheduled.add(call_id)
                name = payload["toolName"]
                tools[name] += 1
                if name == "Bash":
                    command = payload.get("input", {}).get("command")
                    if isinstance(command, str):
                        # Keep only repetition counts, never commands or their hashes.
                        commands[hashlib.sha256(command.encode()).hexdigest()] += 1
            if payload.get("kind") == "result":
                wrapper_failures += payload.get("result", {}).get("success") is False

    http_statuses = Counter(str(request.get("http_status")) for request in requests)
    return {
        "item": item.name,
        "export": export.name,
        "event_sha256": digest(events_path),
        "result_sha256": digest(result_path),
        "worker_outcome": result["outcome"],
        "elapsed_seconds": result["elapsed_seconds"],
        "proxy_requests": len(requests),
        "http_statuses": dict(http_statuses),
        "completed_model_requests": len(completed),
        "completed_requests_match_proxy_count": len(completed) == len(requests),
        "requests_by_source": dict(sources),
        "finish_reasons": dict(finishes),
        "reported_usage": dict(usage),
        "scheduled_tools": dict(tools),
        "tool_wrapper_failures": wrapper_failures,
        "repeated_bash_invocations_beyond_first": sum(n - 1 for n in commands.values()),
        "max_identical_bash_invocations": max(commands.values(), default=0),
        "proxy_request_seconds_sum": round(
            sum(request["elapsed_seconds"] for request in requests), 3
        ),
        "max_request_output_tokens": max(
            (request.get("usage", {}).get("completion_tokens", 0) for request in requests),
            default=0,
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--observations", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    items = [
        summarize(item)
        for item in sorted(args.observations.iterdir())
        if item.is_dir()
        and any((item / stage / "zcode-events.jsonl").is_file() for stage in ("final", "early"))
    ]
    report = {
        "schema_version": 1,
        "scope": "operational telemetry; not scientific review or task acceptance",
        "limitations": [
            "Early exports can contain complete author telemetry but partial task artifacts.",
            "Tool-wrapper success does not establish shell-command or scientific success.",
            "Repeated commands do not establish waste: they may be legitimate polling.",
            "Reported usage includes reused input context and is not unique-token volume.",
            "Request durations may overlap tool durations; do not subtract to infer tool time.",
            "No formal substage boundaries were recorded within these author sessions.",
        ],
        "totals": {
            "items": len(items),
            "proxy_requests": sum(item["proxy_requests"] for item in items),
            "completed_model_requests": sum(item["completed_model_requests"] for item in items),
            "scheduled_tools": sum(sum(item["scheduled_tools"].values()) for item in items),
        },
        "items": items,
    }
    with args.output.open("x") as destination:
        destination.write(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
