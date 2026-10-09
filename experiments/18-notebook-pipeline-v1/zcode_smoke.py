"""Bounded remote ZCode integration check; receives service access only at runtime."""

import base64
import gzip
import hashlib
import http.server
import json
import os
import resource
import signal
import subprocess
import tarfile
import threading
import time
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

from iris.client.client import iris_ctx
from iris.cluster.types import JobName


def file_sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while chunk := source.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def main():
    root = Path.cwd()
    spec = (
        json.loads((root / "run-spec.json").read_text())
        if (root / "run-spec.json").exists()
        else {}
    )
    stage = spec.get("stage", "harness_smoke")
    request_cap = spec.get("request_cap", 4)
    output_cap = spec.get("output_cap", 8192)
    wall_seconds = spec.get("wall_seconds", 240)
    assert stage in {"harness_smoke", "authoring", "repair"}
    assert 1 <= request_cap <= 60 and 1 <= output_cap <= 16384 and 1 <= wall_seconds <= 1200
    token = os.environ.pop("GLM_BULK_TOKEN")
    relay = os.environ.pop("GLM_ENDPOINT_JOB")
    upstream = (
        iris_ctx()
        .client.resolver_for_job(JobName.from_string(relay))
        .resolve("glm-5.3")
        .endpoints[0]
        .url.rstrip("/")
    )
    if not upstream.endswith("/v1"):
        upstream += "/v1"
    node_version = "v24.14.0"
    archive_name = f"node-{node_version}-linux-x64.tar.xz"
    node_url = f"https://nodejs.org/dist/{node_version}/"
    archive = root / archive_name
    urllib.request.urlretrieve(node_url + archive_name, archive)
    expected = next(
        line.split()[0]
        for line in urllib.request.urlopen(node_url + "SHASUMS256.txt", timeout=30)
        .read()
        .decode()
        .splitlines()
        if line.split()[-1] == archive_name
    )
    assert hashlib.sha256(archive.read_bytes()).hexdigest() == expected
    with tarfile.open(archive) as src:
        src.extractall(root, filter="data")
    node = root / archive_name.removesuffix(".tar.xz") / "bin/node"
    assert hashlib.sha256((root / "zcode.cjs").read_bytes()).hexdigest() == (
        "fad4c35c4c36ec210d8a06d3fa0e77de23c8545e2eb6ff90aea1eb38d1e6275f"
    )
    requests = []
    mutex = threading.Lock()

    class Proxy(http.server.BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_POST(self):
            if self.path != "/v1/chat/completions":
                self.send_error(403, "Only chat completions are enabled")
                return
            data = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            with mutex:
                if len(requests) >= request_cap or data.get("model") != "glm-5.3":
                    self.send_error(403, "Model or smoke request budget rejected")
                    return
                record = {
                    "index": len(requests),
                    "model": data["model"],
                    "message_count": len(data.get("messages", [])),
                    "tool_count": len(data.get("tools", [])),
                    "tool_names": [
                        t.get("function", {}).get("name") for t in data.get("tools", [])
                    ],
                    "model_parameters": {
                        k: v
                        for k, v in data.items()
                        if k
                        in {
                            "temperature",
                            "top_p",
                            "reasoning_effort",
                            "thinking",
                            "chat_template_kwargs",
                        }
                    },
                }
                requests.append(record)
                print(
                    "BIOTASKS_MODEL_REQUEST "
                    + json.dumps(
                        {"index": record["index"], "stage": stage, "model": data["model"]}
                    ),
                    flush=True,
                )
            data.pop("max_completion_tokens", None)
            data["max_tokens"] = min(data.get("max_tokens") or output_cap, output_cap)
            record["max_tokens"] = data["max_tokens"]
            start = time.monotonic()
            try:
                req = urllib.request.Request(
                    upstream + "/chat/completions",
                    data=json.dumps(data).encode(),
                    headers={
                        "Authorization": "Bearer " + token,
                        "Content-Type": "application/json",
                    },
                )
                with urllib.request.urlopen(req, timeout=150) as response:
                    record["http_status"] = response.status
                    self.send_response(response.status)
                    self.send_header("Content-Type", response.headers.get("Content-Type"))
                    self.end_headers()
                    pending = b""
                    while chunk := response.read1(16384):
                        pending += chunk
                        while b"\n" in pending:
                            line, pending = pending.split(b"\n", 1)
                            if line.startswith(b"data: ") and line != b"data: [DONE]":
                                try:
                                    event = json.loads(line[6:])
                                    if event.get("usage"):
                                        record["usage"] = event["usage"]
                                except ValueError:
                                    pass
                        self.wfile.write(chunk)
                        self.wfile.flush()
            except urllib.error.HTTPError as exc:
                record["http_status"] = exc.code
                self.send_error(502, "Upstream rejected request")
            except Exception as exc:
                record["error_type"] = type(exc).__name__
            finally:
                record["elapsed_seconds"] = round(time.monotonic() - start, 3)
                print(
                    "BIOTASKS_MODEL_RESPONSE "
                    + json.dumps(
                        {
                            k: v
                            for k, v in record.items()
                            if k in {"index", "http_status", "elapsed_seconds", "error_type"}
                        }
                    ),
                    flush=True,
                )

    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Proxy)
    server.daemon_threads = True
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    workspace = root / "author-workspace"
    workspace.mkdir()
    if (root / "inputs.zip").exists():
        if (
            spec.get("input_zip_sha256")
            and file_sha256(root / "inputs.zip") != spec["input_zip_sha256"]
        ):
            raise ValueError("Authoring input archive checksum mismatch")
        with zipfile.ZipFile(root / "inputs.zip") as archive:
            for member in archive.infolist():
                target = (workspace / member.filename).resolve()
                if (
                    not target.is_relative_to(workspace.resolve())
                    or member.file_size > 32 * 1024 * 1024
                ):
                    raise ValueError("Unsafe authoring input archive")
            archive.extractall(workspace)
    original_inputs = {
        str(p.relative_to(workspace)): file_sha256(p) for p in workspace.rglob("*") if p.is_file()
    }
    state = root / "zcode-state"
    state.mkdir()
    config = {
        "features": {"mcp": False},
        "plugins": {"enabled": False},
        "memory": {"enabled": False},
        "skills": {"enabled": False},
        "toolConcurrency": {"maxConcurrency": 1},
    }
    user_config = Path.home() / ".zcode/cli/config.json"
    user_config.parent.mkdir(parents=True, exist_ok=True)
    # This runs only in a fresh disposable job container, never on the shared VM.
    user_config.write_text(json.dumps(config))
    personal = {
        "schemaVersion": 1,
        "config": {
            "providerConfigRules": {
                "providerRules": [
                    {
                        "providerId": "biotasks",
                        "providerName": "BioTasks bounded service",
                        "enabled": True,
                        "config": {
                            "group": "standard-personal",
                            "access": {"type": "api-key", "apiKey": "local-proxy"},
                            "api": {
                                "type": "openai-chat-completions",
                                "baseUrl": f"http://127.0.0.1:{server.server_port}/v1",
                            },
                            "personalModelIds": ["glm-5.3"],
                        },
                    }
                ]
            },
            "modelConfigRules": {
                "manualProviderModelRules": [],
                "providerModelRules": [
                    {
                        "providerId": "biotasks",
                        "modelId": "glm-5.3",
                        "config": {
                            "enabled": True,
                            "properties": {"contextWindow": 131072},
                            "optionSpecs": {"maxOutputTokens": {"max": output_cap}},
                        },
                    }
                ],
            },
            "defaultModelSelection": {
                "providerId": "biotasks",
                "modelId": "glm-5.3",
                "options": {"reasoningLevel": "low"},
            },
        },
    }
    (state / "provider.json").write_text(json.dumps(personal))
    env = os.environ | {
        "ZCODE_STORAGE_DIR": str(state / "cli"),
        "ZCODE_BUILTIN_PROVIDER_CONFIG_FILE": str(root / "zcode-builtin.json"),
        "ZCODE_BUILTIN_PROVIDER_BUNDLED_CONFIG_FILE": str(root / "zcode-builtin.json"),
        "ZCODE_PERSONAL_PROVIDER_CONFIG_FILE": str(state / "provider.json"),
        "ZCODE_MAX_TOOL_CONCURRENCY": "1",
        "PATH": str(node.parent) + ":" + os.environ.get("PATH", ""),
    }
    prompt = spec.get(
        "prompt",
        "Write the exact text READY followed by a newline to readiness.txt in the current workspace. Then stop. Do not use other agents, web access or unrelated tools.",
    )
    start = time.monotonic()
    with (
        (root / "zcode-events.jsonl").open("wb") as out,
        (root / "zcode-stderr.txt").open("wb") as err,
    ):
        process = subprocess.Popen(
            [
                str(node),
                str(root / "zcode.cjs"),
                "--cwd",
                str(workspace),
                "--prompt",
                prompt,
                "--output-format",
                "stream-json",
                "--locale",
                "en-US",
            ],
            env=env,
            stdout=out,
            stderr=err,
            start_new_session=True,
        )
        timed_out = False
        try:
            process.wait(timeout=wall_seconds)
        except subprocess.TimeoutExpired:
            timed_out = True
            os.killpg(process.pid, signal.SIGKILL)
            process.wait()
    server.shutdown()
    marker = workspace / "readiness.txt"
    result = {
        "stage": stage,
        "scientific_task": stage != "harness_smoke",
        "zcode_cli_version": "0.16.9",
        "release": "3.14.5",
        "exit_code": process.returncode,
        "timed_out": timed_out,
        "elapsed_seconds": round(time.monotonic() - start, 3),
        "requests": requests,
        "marker_matches": marker.exists() and marker.read_text() == "READY\n",
        "peak_child_rss_kib": resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss,
        "outcome": "request_budget_exhausted"
        if process.returncode and len(requests) >= request_cap
        else "timeout"
        if timed_out
        else "worker_finished"
        if process.returncode == 0
        else "worker_failed",
    }
    artifacts = {
        "result.json": json.dumps(result),
        "zcode-events.jsonl": (root / "zcode-events.jsonl").read_text(errors="replace"),
        "zcode-stderr.txt": (root / "zcode-stderr.txt").read_text(errors="replace"),
    }
    if stage != "harness_smoke":
        # Preserve all generated task files in private object storage, including binary inputs.
        # Original inputs are separately archived. Preserve scientific intermediates too.
        import fsspec

        prefix = os.environ["BIOTASKS_ARTIFACT_PREFIX"].rstrip("/")
        if not prefix.startswith("s3://"):
            raise ValueError("Private durable artifact prefix required")
        manifest = []
        generated = [
            p
            for p in workspace.rglob("*")
            if p.is_file()
            and not p.is_symlink()
            and p.resolve().is_relative_to(workspace.resolve())
            and not set(p.relative_to(workspace).parts)
            & {".git", ".zcode", ".venv", "node_modules", "__pycache__", ".cache"}
            and file_sha256(p) != original_inputs.get(str(p.relative_to(workspace)))
        ]
        for path in generated:
            relative = str(path.relative_to(workspace))
            digest = hashlib.sha256()
            with (
                path.open("rb") as src,
                fsspec.open(prefix + "/workspace/" + relative, "wb").open() as dst,
            ):
                while chunk := src.read(1024 * 1024):
                    if token.encode() in chunk:
                        raise ValueError("Credential detected in generated artifact")
                    digest.update(chunk)
                    dst.write(chunk)
            manifest.append(
                {"path": relative, "size": path.stat().st_size, "sha256": digest.hexdigest()}
            )
            if (
                path.suffix in {".md", ".py", ".sh", ".toml", ".json", ".txt"}
                or path.name == "Dockerfile"
            ) and path.stat().st_size < 256 * 1024:
                artifacts["workspace/" + relative] = path.read_text(errors="replace")
        artifacts["artifact-manifest.json"] = json.dumps(manifest)
        artifacts["input-manifest.json"] = json.dumps(original_inputs)
        if (root / "inputs.zip").exists():
            with (
                (root / "inputs.zip").open("rb") as src,
                fsspec.open(prefix + "/inputs.zip", "wb").open() as dst,
            ):
                while chunk := src.read(1024 * 1024):
                    dst.write(chunk)
        result["durable_artifact_count"] = len(manifest)
        artifacts["result.json"] = json.dumps(result)
        for name, value in artifacts.items():
            clean = value.replace(token, "[REDACTED]").replace(upstream, "[ENDPOINT]")
            with fsspec.open(prefix + "/records/" + name, "wt").open() as dst:
                dst.write(clean)
    # Only explicitly selected artifacts; no provider config, environment or credentials.
    encoded = json.dumps(artifacts).replace(token, "[REDACTED]").replace(upstream, "[ENDPOINT]")
    print("BIOTASKS_SMOKE_RESULT " + json.dumps(result), flush=True)
    packed = gzip.compress(encoded.encode())
    export = base64.b64encode(packed).decode()
    pieces = [export[i : i + 6000] for i in range(0, len(export), 6000)]
    print(
        "BIOTASKS_SMOKE_ARCHIVE "
        + json.dumps({"chunks": len(pieces), "sha256": hashlib.sha256(packed).hexdigest()}),
        flush=True,
    )
    for index, piece in enumerate(pieces):
        print(f"BIOTASKS_SMOKE_CHUNK {index} {piece}", flush=True)


if __name__ == "__main__":
    main()
