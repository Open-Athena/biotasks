"""Bounded read-only metadata/notices preparation; no task or environment repair."""

import base64
import hashlib
import json
import shutil
import subprocess
from pathlib import Path

BASE = Path(__file__).parent.resolve()
OLD = BASE.parents[2] / "53/experiments/53-installed-native"


def save(path, value):
    path.write_text(json.dumps(value, indent=2) + "\n")


def get(path):
    result = subprocess.run(["gh", "api", path], check=True, capture_output=True, timeout=60)
    assert len(result.stdout) < 2 * 1024**2
    return json.loads(result.stdout)


def blob(path, ref):
    value = get("repos/biopython/biopython/contents/" + path + "?ref=" + ref)
    data = base64.b64decode(value["content"])
    identity = hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()
    assert identity == value["sha"]
    return value, data


def main():
    config = json.loads((OLD / "native-config.json").read_text())
    config["repo"] = {
        "url": "https://github.com/biopython/biopython",
        "ref": "2fbe8755bb44731e60b7bd1e2cc55cf34d94e15b",
        "access": "public",
    }
    config["pipeline"]["options"] = {"limit": 50, "since": "2026-10-18", "until": "2026-10-19"}
    config["output"]["dataset_name"] = "biotasks57-biopython"
    save(BASE / "native-config.json", config)
    shutil.copyfile(OLD / "backend.json", BASE / "backend.json")
    notices = BASE / "notices"
    (notices / "biopython").mkdir(parents=True)
    shutil.copytree(OLD / "notices/repo2rlenv", notices / "repo2rlenv")
    refs = {config["repo"]["ref"]}
    for number in [5372, 5382]:
        meta = json.loads((BASE / f"pr{number}-metadata.json").read_text())
        refs.update([meta["base"]["sha"], meta["head"]["sha"]])
    rows = []
    for ref in sorted(refs):
        meta, data = blob("LICENSE.rst", ref)
        assert b"Permission to use, copy, modify, and distribute" in data
        assert b"Biopython License Agreement" in data and b"BSD 3-Clause License" in data
        filename = ref + "-LICENSE.rst"
        (notices / "biopython" / filename).write_bytes(data)
        rows.append(
            {
                "ref": ref,
                "path": "LICENSE.rst",
                "git_blob": meta["sha"],
                "sha256": hashlib.sha256(data).hexdigest(),
                "notice": "biopython/" + filename,
            }
        )
    headers = []
    for number in [5372, 5382]:
        meta = json.loads((BASE / f"pr{number}-metadata.json").read_text())
        paths = [v["filename"] for v in json.loads((BASE / f"pr{number}-files.json").read_text())]
        assert all(x.endswith((".py", ".rst")) for x in paths), paths
        for key in ["base", "head"]:
            ref = meta[key]["sha"]
            for name in paths:
                if not name.endswith(".py"):
                    continue
                value, data = blob(name, ref)
                header = b"".join(data.splitlines(keepends=True)[:60])
                filename = str(number) + "-" + key + "-" + name.replace("/", "_") + ".txt"
                (notices / "biopython" / filename).write_bytes(header)
                headers.append(
                    {
                        "pr": number,
                        "side": key,
                        "ref": ref,
                        "path": name,
                        "git_blob": value["sha"],
                        "source_sha256": hashlib.sha256(data).hexdigest(),
                        "header_notice": "biopython/" + filename,
                    }
                )
    save(
        notices / "SOURCE.json",
        {
            "repo": config["repo"],
            "licenses": rows,
            "file_headers": headers,
            "scope": "Complete pinned project terms and original changed-source headers; no images/environments/biological datasets",
        },
    )
    print(
        json.dumps(
            {"pinned_license_refs": len(rows), "source_headers": len(headers), "new_model_jobs": 0}
        )
    )


if __name__ == "__main__":
    main()
