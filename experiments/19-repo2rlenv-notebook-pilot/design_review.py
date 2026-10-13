"""One direct design call for prompt review; no construction, tools or retries."""

import base64
import hashlib
import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path


def main():
    from iris.client.client import iris_ctx
    from iris.cluster.types import JobName

    request = json.loads(Path("request.json").read_text())
    endpoint = (
        iris_ctx()
        .client.resolver_for_job(JobName.from_string(os.environ["GLM_ENDPOINT_JOB"]))
        .resolve("glm-5.3")
        .endpoints[0]
        .url.rstrip("/")
    )
    if not endpoint.endswith("/v1"):
        endpoint += "/v1"
    started = time.time()
    result = {"requests": 1, "started_at_unix": started}
    try:
        req = urllib.request.Request(
            endpoint + "/chat/completions",
            data=json.dumps(request).encode(),
            headers={
                "Authorization": "Bearer " + os.environ["GLM_BULK_TOKEN"],
                "Content-Type": "application/json",
            },
        )
        with urllib.request.urlopen(req, timeout=1200) as response:
            data = response.read(2_000_001)
        if len(data) > 2_000_000:
            raise ValueError("Response exceeds review artifact bound")
        result.update(status="completed", response=json.loads(data))
    except urllib.error.HTTPError as exc:
        result.update(status="http_error", http_status=exc.code)
    except Exception as exc:
        # Raw exception strings may contain the private service route.
        result.update(status="failed", exception_type=type(exc).__name__)
    result["elapsed_seconds"] = time.time() - started
    data = json.dumps(result).encode()
    print("DESIGN_MANIFEST " + json.dumps({"sha256": hashlib.sha256(data).hexdigest()}), flush=True)
    encoded = base64.b64encode(data).decode()
    for offset in range(0, len(encoded), 16000):
        print(
            "DESIGN_CHUNK "
            + json.dumps({"offset": offset, "data": encoded[offset : offset + 16000]}),
            flush=True,
        )
    print("DESIGN_COMPLETE", flush=True)


if __name__ == "__main__":
    main()
