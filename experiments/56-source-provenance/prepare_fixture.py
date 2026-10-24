"""Create own synthetic pure-Python packaging inputs; never biology code."""

import argparse
import json
import re
import shutil
from pathlib import Path

root = Path(__file__).resolve().parent
parser = argparse.ArgumentParser()
parser.add_argument("--id", default="001")
args = parser.parse_args()
assert re.fullmatch(r"[0-9]{3}", args.id)
target = root / "inputs-private" / ("local-probe-" + args.id)
if target.exists():
    raise RuntimeError("Keep existing fixture state; use a separately recorded run")
target.mkdir(parents=True)
records = []
for folder, name, version, origin, dependencies in (
    ("checkout", "biotasks56-target", "0.0.0", "checkout", []),
    ("release", "biotasks56-target", "1.0.0", "release", []),
    ("companion", "biotasks56-companion", "1.0.0", "companion", ["biotasks56-target>=1.0.0"]),
):
    directory = target / folder
    module = name.replace("-", "_")
    package = directory / "src" / module
    package.mkdir(parents=True)
    (package / "__init__.py").write_text(f"ORIGIN = {origin!r}\n")
    (directory / "pyproject.toml").write_text(
        '[build-system]\nrequires = ["uv_build==0.12.21"]\nbuild-backend = "uv_build"\n\n'
        f'[project]\nname = "{name}"\nversion = "{version}"\nrequires-python = ">=3.13"\n'
        f"dependencies = {json.dumps(dependencies)}\n"
    )
    if folder == "checkout":
        # Pip drives a real editable install/direct_url record. The tiny local
        # fixture backend avoids downloading tools during the offline check;
        # it is not a replacement backend or install recipe for AnnData.
        shutil.copyfile(root / "fixture_backend.py", directory / "fixture_backend.py")
        text = (directory / "pyproject.toml").read_text()
        text = text.replace('requires = ["uv_build==0.12.21"]', "requires = []")
        text = text.replace(
            'build-backend = "uv_build"', 'build-backend = "fixture_backend"\nbackend-path = ["."]'
        )
        (directory / "pyproject.toml").write_text(text)
    records.append(
        {
            "path": str(directory),
            "project": name,
            "version": version,
            "module": module,
            "dependencies": dependencies,
        }
    )
(target / "wheels").mkdir()
(target / "tmp").mkdir()
(root / ("fixture-inputs-" + args.id + ".json")).write_text(
    json.dumps(
        {
            "synthetic": True,
            "biological_input": False,
            "not_anndata_execution": True,
            "projects": records,
        },
        indent=2,
    )
    + "\n"
)
print(json.dumps(records, indent=2))
