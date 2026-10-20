"""Read Docker /version only; do not build, create, start, stop or delete anything."""

import hashlib
import http.client
import json
import os
import socket
from pathlib import Path


class LocalDockerConnection(http.client.HTTPConnection):
    def connect(self):
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.settimeout(10)
        self.sock.connect("/var/run/docker.sock")


def main():
    report = {
        "model_calls": 0, "target_code_executed": False,
        "docker_api_requests": ["GET /version"],
        "docker_socket_present": Path("/var/run/docker.sock").exists(),
    }
    if report["docker_socket_present"]:
        connection = LocalDockerConnection("localhost", timeout=10)
        try:
            connection.request("GET", "/version")
            response = connection.getresponse()
            report["status"] = response.status
            raw = response.read(64 * 1024)
            if response.status == 200:
                data = json.loads(raw)
                report["docker_version"] = data.get("Version")
                report["docker_api_version"] = data.get("ApiVersion")
        except Exception as exc:
            report["error_type"] = type(exc).__name__
        finally:
            connection.close()
    raw = (json.dumps(report, sort_keys=True, indent=2) + "\n").encode()
    output = Path(os.environ["IRIS_OUTPUT_DIR"])
    output.mkdir(parents=True, exist_ok=True)
    (output / "docker-access.json").write_bytes(raw)
    print("BIOTASKS24_DOCKER_ACCESS " + json.dumps(report, sort_keys=True), flush=True)
    print("BIOTASKS24_DOCKER_ACCESS_SHA256 " + hashlib.sha256(raw).hexdigest(), flush=True)


if __name__ == "__main__":
    main()
