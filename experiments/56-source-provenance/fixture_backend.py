"""Dependency-free PEP660 backend for our synthetic editable fixture only."""

import base64
import hashlib
import zipfile
from pathlib import Path


def get_requires_for_build_editable(config_settings=None):
    return []


def build_editable(wheel_directory, config_settings=None, metadata_directory=None):
    name, version = "biotasks56_target", "0.0.0"
    info = name + "-" + version + ".dist-info"
    entries = {
        name + ".pth": str(Path(__file__).parent / "src") + "\n",
        info + "/METADATA": "Metadata-Version: 2.1\nName: biotasks56-target\nVersion: 0.0.0\n\n",
        info
        + "/WHEEL": "Wheel-Version: 1.0\nGenerator: biotasks56-synthetic\nRoot-Is-Purelib: true\nTag: py3-none-any\n",
    }
    record = []
    for path, content in entries.items():
        raw = content.encode()
        digest = base64.urlsafe_b64encode(hashlib.sha256(raw).digest()).decode().rstrip("=")
        record.append(f"{path},sha256={digest},{len(raw)}\n")
    record.append(info + "/RECORD,,\n")
    entries[info + "/RECORD"] = "".join(record)
    filename = name + "-" + version + "-py3-none-any.whl"
    with zipfile.ZipFile(Path(wheel_directory) / filename, "w") as archive:
        for path, content in entries.items():
            archive.writestr(zipfile.ZipInfo(path, date_time=(2020, 1, 1, 0, 0, 0)), content)
    return filename
