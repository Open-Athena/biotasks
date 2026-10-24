"""Read only the original submitted job through its frozen configured SDK."""

import json
import sys
import types
from datetime import UTC, datetime
from pathlib import Path

# Same namespace-only ABI isolation as the installed transport bridge. The
# configured SDK owns all dependencies; no main-runtime site-packages injection.
package = types.ModuleType("biotasks")
package.__path__ = [sys.argv[1]]
sys.modules["biotasks"] = package
from biotasks.validation import iris_client, preservation  # noqa: E402
from biotasks.validation.files import read_json, require, sha, write_json  # noqa: E402

root = Path(__file__).resolve().parent
plan = read_json(root / "inputs-private/run-001/anndata/plan.json")
require(iris_client.fingerprint() == plan["client_profile"], "Observer SDK changed")
require(sha(Path(plan["backend"]["config"])) == plan["backend_config_sha256"], "Observer config changed")
job_id = "/exedev/" + plan["group"]["run_id"]
receipt = read_json(root / "inputs-private/run-001/anndata/runs/generation/submission.json")
require(receipt["job_id"] == job_id, "Wrong observation handle")
name = iris_client.module("iris.cluster.types").JobName.from_string(job_id)
with iris_client.connect(plan["backend"]["config"]) as client:
    rows = list(client.job(name).logs(max_lines=40, tail=True))
values = [{"timestamp_epoch_seconds": row.timestamp.epoch_seconds(), "source": row.source, "data": row.data, "attempt_id": row.attempt_id, "key": row.key} for row in rows]
raw = json.dumps(values, indent=2).encode()
require(len(raw) <= 512 * 1024, "Observer log bound")
preservation.inspect(raw, "native-log-observation.json")
stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
target = root / "inputs-private" / ("native-log-observation-" + stamp + ".json")
write_json(target, {"observed_utc": stamp, "job_id": job_id, "rows": values, "read_only": True, "observer_new_model_calls": 0, "job_model_usage": "not_observed_by_this_query"})
print(json.dumps({"job_id": job_id, "path": str(target), "rows": len(rows), "read_only": True, "observer_new_model_calls": 0}))
