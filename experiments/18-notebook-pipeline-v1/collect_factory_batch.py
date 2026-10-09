"""Take one bounded snapshot of batch states and exported text logs; never retry."""

import argparse
import datetime
import json
import re
import sqlite3
from pathlib import Path

from decode_log_archive import decode

from biotasks.factory_stage import STAGE_ROLES


def observation_directory(output: Path, seed: str, session: str) -> Path:
    """Keep repeated stages for one seed separate and reject ambiguous identities."""
    parts = session.split(":")
    if (
        len(parts) != 3
        or not re.fullmatch(r"[0-9a-f]{64}", parts[0])
        or parts[1] != seed
        or not re.fullmatch(r"[a-z0-9-]+", seed)
        or parts[2] not in {*STAGE_ROLES, "seed_pipeline"}
    ):
        raise ValueError("Invalid factory session identity")
    destination = output / parts[0] / seed / parts[2]
    destination.mkdir(parents=True, exist_ok=False)
    return destination


def main():
    from iris.cli.connect import connect_controller
    from iris.client.client import IrisClient
    from iris.cluster.types import JobName

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--private-config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    config = json.loads(args.private_config.read_text())
    with sqlite3.connect(args.ledger) as db:
        sessions = db.execute("SELECT id,seed,job_id FROM sessions ORDER BY seed").fetchall()
    args.output.mkdir(exist_ok=False)
    records = []
    with connect_controller(config_file=Path(config["controller_config"])) as endpoint:
        with IrisClient.remote(endpoint.url, credentials=endpoint.credentials) as client:
            for session, seed, job_id in sessions:
                row = {"session": session, "seed": seed, "job_id": job_id}
                if not job_id:
                    row["state"] = "submission_unresolved"
                    records.append(row)
                    continue
                job = client.job(JobName.from_string(job_id))
                state = job.status()
                row["state"] = state.state.name
                destination = observation_directory(args.output, seed, session)
                row["artifact_directory"] = str(destination.relative_to(args.output))
                row["stage_slot"] = session.rsplit(":", 1)[-1]
                logs = destination / "logs.json"
                # Stream the JSON array so a large export never accumulates in memory.
                with logs.open("x") as stream:
                    stream.write("[")
                    count = 0
                    for line in job.logs(max_lines=3000, substring="BIOTASKS_"):
                        if count:
                            stream.write(",\n")
                        stream.write(json.dumps(line.data))
                        count += 1
                    stream.write("]\n")
                row["log_lines"] = count
                if row["stage_slot"] == "seed_pipeline":
                    values = json.loads(logs.read_text())
                    summaries = [
                        json.loads(value.split("BIOTASKS_PIPELINE ", 1)[1])
                        for value in values
                        if "BIOTASKS_PIPELINE " in value
                    ]
                    row["pipeline"] = summaries[-1] if summaries else None
                row["exports"] = {}
                for stage in ["early", "final"]:
                    try:
                        row["exports"][stage] = decode(logs, destination / stage, stage)
                    except ValueError as error:
                        row["exports"][stage] = {"recovered": False, "reason": str(error)}
                records.append(row)
                # Keep every completed observation if a later network read fails.
                (destination / "observation.json").write_text(json.dumps(row, indent=2) + "\n")
                print(
                    json.dumps({"seed": seed, "state": row["state"], "log_lines": count}),
                    flush=True,
                )
    (args.output / "observations.json").write_text(
        json.dumps(
            {
                "schema_version": 2,
                "observed_at": datetime.datetime.now(datetime.UTC).isoformat(),
                "jobs": records,
            },
            indent=2,
        )
        + "\n"
    )


if __name__ == "__main__":
    main()
