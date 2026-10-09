"""Run one checkpointed Harbor job, or clean up its explicitly recorded sandboxes."""

import asyncio
import json
import os
import sys
from pathlib import Path


async def run():
    from harbor.job import Job
    from harbor.models.job.config import JobConfig

    config = JobConfig.model_validate_json(Path("harbor-job.json").read_text())
    result = await Job(config).run()
    Path("harbor-result.json").write_text(result.model_dump_json(indent=2))


def cleanup():
    from daytona import Daytona, DaytonaConfig

    client = Daytona(DaytonaConfig(api_key=os.environ["DAYTONA_API_KEY"]))
    path = Path(os.environ["BIOTASKS_OWNED_SANDBOXES"])
    ids = (
        {json.loads(line)["id"] for line in path.read_text().splitlines()}
        if path.exists()
        else set()
    )
    records = []
    for sandbox_id in sorted(ids):
        try:
            client.delete(client.get(sandbox_id), timeout=60, wait=True)
            try:
                client.get(sandbox_id)
            except Exception as error:
                # Do not interpret an arbitrary API failure as verified deletion.
                from daytona import DaytonaNotFoundError

                if not isinstance(error, DaytonaNotFoundError):
                    raise
            else:
                raise RuntimeError("Sandbox still retrievable after deletion")
            records.append({"id": sandbox_id, "deleted": True})
        except Exception as error:
            records.append({"id": sandbox_id, "deleted": False, "error_type": type(error).__name__})
    Path("cleanup.json").write_text(json.dumps(records, indent=2))
    if any(not record["deleted"] for record in records):
        raise RuntimeError("Owned sandbox cleanup incomplete; see private cleanup record")


if __name__ == "__main__":
    if sys.argv[1:] == ["cleanup"]:
        cleanup()
    else:
        asyncio.run(run())
