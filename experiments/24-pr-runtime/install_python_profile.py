"""Generic development profile: install project and declared test dependencies."""

import json
import subprocess
import sys
import tomllib
from pathlib import Path

data = tomllib.loads(Path("/workspace/pyproject.toml").read_text())
build_requirements = data.get("build-system", {}).get("requires", [])
if build_requirements:
    subprocess.run([sys.executable, "-m", "pip", "install", *build_requirements], check=True)
optional = data.get("project", {}).get("optional-dependencies", {})
extras = [name for name in ("test", "tests", "testing") if name in optional]
requirement = ".[%s]" % ",".join(extras) if extras else "."
subprocess.run([sys.executable, "-m", "pip", "install", "-e", requirement], check=True)
groups = data.get("dependency-groups", {})


def dependencies(name, ancestors=()):
    if name in ancestors:
        raise ValueError("Cyclic test dependency group")
    for item in groups[name]:
        if isinstance(item, str):
            yield item
        else:
            yield from dependencies(item["include-group"], (*ancestors, name))


requirements = ["pytest"]
for name in ("test", "tests", "testing"):
    if name in groups:
        requirements.extend(dependencies(name))
subprocess.run([sys.executable, "-m", "pip", "install", *requirements], check=True)
print(json.dumps({
    "extras": extras, "test_requirements": requirements, "build_requirements": build_requirements,
}))
