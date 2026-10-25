"""Three synthetic environment controls in the existing bounded provider runner.

Requires separate funding and shared-pool admission. No model or biology runs.
"""

import argparse
import asyncio
import hashlib
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location(
    "final_environment_compat_base",
    HERE / "factory-checks/daytona-session-transport/run_live_check.py",
)
base = importlib.util.module_from_spec(spec)
spec.loader.exec_module(base)

SETUP = """import hashlib,json,sysconfig,venv
from pathlib import Path
venv.EnvBuilder(with_pip=False).create('/work/venv')
Path('/inputs').mkdir(exist_ok=True)
data=Path('/inputs/data.csv'); data.write_bytes(b'value\\n3\\n')
Path('/work/reference').mkdir(exist_ok=True)
Path('/work/reference/final.csv').write_bytes(data.read_bytes())
Path('/work/original-inputs.json').write_text(json.dumps({'files':[
 {'local_path':str(data),'bytes':data.stat().st_size,'sha256':hashlib.sha256(data.read_bytes()).hexdigest()}]}))
"""

INSTALLED = """import hashlib,json,sysconfig
from pathlib import Path
root=Path(sysconfig.get_path('purelib'))
asset=root/'synthetic/tests/final.csv';asset.parent.mkdir(parents=True)
asset.write_bytes(b'value\\n3\\n')
meta=root/'synthetic_tests-0.1.dist-info';meta.mkdir()
(meta/'METADATA').write_text('Name: synthetic-tests\\nVersion: 0.1\\n')
(meta/'RECORD').write_text('synthetic/tests/final.csv,,\\n')
print(json.dumps({'distribution':'synthetic-tests','path':'synthetic/tests/final.csv',
 'sha256':hashlib.sha256(asset.read_bytes()).hexdigest(),
 'reason':'Synthetic worker-selected unused expected-output fixture; copy programs never import it'}))
"""

DERIVE = """import argparse,json,shutil
from pathlib import Path
p=argparse.ArgumentParser()
p.add_argument('--source-inputs');p.add_argument('--reference-dir');p.add_argument('--destination')
a=p.parse_args();d=Path(a.destination)
(d/'inputs').mkdir(parents=True);(d/'reference').mkdir()
source=json.loads(Path(a.source_inputs).read_text())['files'][0]['local_path']
shutil.copyfile(source,d/'inputs/data.csv')
shutil.copyfile(Path(a.reference_dir)/'final.csv',d/'reference/final.csv')
"""

ORACLE = """import argparse,shutil
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--input-dir');p.add_argument('--output-dir')
a=p.parse_args();shutil.copyfile(Path(a.input_dir)/'data.csv',Path(a.output_dir)/'final.csv')
"""


async def checks(remote, root):
    # The shared runner creates an offline sandbox; no dependency download is needed.
    for name in ("materialization_remote.py", "grading_remote.py", "dependency_assets.py"):
        await remote.upload(HERE / name, "/work/" + name)

    async def command(argv, label):
        reply = await remote.command(argv, 60, label)
        if reply["exit_code"] or reply["timed_out"]:
            raise RuntimeError("Synthetic environment control failed: " + json.dumps(reply))
        return reply

    await command(["python", "-c", SETUP], "synthetic-setup")
    await command(["python", "/work/grading_remote.py", "initialize"], "synthetic-roles")
    removal = json.loads(
        (await command(["/work/venv/bin/python", "-c", INSTALLED], "synthetic-installed"))["log"]
    )
    request = {
        "input_paths": ["data.csv"],
        "output_paths": ["final.csv"],
        "derive_code": DERIVE,
        "oracle_code": ORACLE,
        "original_source": "result = data.copy()\n",
        "seconds": 30,
        "new_dependency_exclusions": {"files": []},
        "effective_dependency_exclusions": {"files": []},
    }
    observed = []
    for name, files in (("before-final-removal", []), ("after-final-removal", [removal])):
        request["new_dependency_exclusions"] = {"files": files}
        request["effective_dependency_exclusions"] = {"files": files}
        path = root / (name + "-request.json")
        path.write_text(json.dumps(request, indent=2) + "\n")
        await remote.upload(path, "/work/grading-private/materialization.json")
        result = json.loads(
            (await command(["python", "/work/materialization_remote.py"], name))["log"]
        )
        if result["status"] != "executed_requires_scientific_validation":
            raise RuntimeError("Synthetic controlled programs did not succeed")
        catalog = root / (name + "-catalog.json")
        await remote.download("/work/grading-private/dependency-assets-final.json", catalog)
        identity = result["environment"]["asset_catalog"]
        assert catalog.stat().st_size == identity["bytes"]
        assert hashlib.sha256(catalog.read_bytes()).hexdigest() == identity["sha256"]
        records = json.loads(catalog.read_text())["files"]
        assert any(row["path"] == removal["path"] for row in records) == (not files)
        assert result["environment"]["removal_receipt"]["excluded_files_absent"]
        if observed:
            assert all(
                result[k] == observed[0][k] for k in ("inputs", "reference", "oracle_outputs")
            )
        (root / (name + "-result.json")).write_text(json.dumps(result, indent=2) + "\n")
        observed.append(result)
    # Restoring the exact fixture must fail the read-only absence check.
    restore = "import sysconfig;from pathlib import Path;(Path(sysconfig.get_path('purelib'))/'synthetic/tests/final.csv').write_bytes(b'value\\n3\\n')"
    await command(["/work/venv/bin/python", "-c", restore], "restore-synthetic-answer")
    reply = await remote.command(
        [
            "/work/venv/bin/python",
            "/work/dependency_assets.py",
            "verify-absence",
            "/work/grading-private/materialization.json",
            "/work/grading-private/recheck.json",
        ],
        30,
        "restored-answer-rejected",
    )
    assert reply["exit_code"] != 0 and not reply["timed_out"]
    return [
        {"name": "final-inventory-exposes-fixture", "passed": True},
        {"name": "declared-removal-and-fresh-controlled-programs", "passed": True},
        {"name": "restored-answer-rejected", "passed": True},
    ]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("config", type=Path)
    parser.add_argument("root", type=Path)
    args = parser.parse_args()
    print(
        json.dumps(
            asyncio.run(base.run(json.loads(args.config.read_text()), args.root, checks=checks))
        )
    )
