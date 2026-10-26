"""Synthetic provider checks for installed hints, role privacy and invalidation.

The shared runner requires a separately funded, admitted slot. This script makes
no model calls, downloads no biological inputs and never qualifies a task.
"""

import argparse
import asyncio
import hashlib
import importlib.util
import json
import time
from pathlib import Path

HERE = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location(
    "installed_hints_compat_base",
    HERE / "factory-checks/final-environment/run_live_check.py",
)
base = importlib.util.module_from_spec(spec)
spec.loader.exec_module(base)

SETUP = base.SETUP.replace("value\\n3\\n", "value\\n-4.9275633\\n")
INSTALLED = """import hashlib,json,sysconfig
from pathlib import Path
root=Path(sysconfig.get_path('purelib'))
package=root/'synthetic';package.mkdir()
(package/'__init__.py').write_text("raise RuntimeError('DO NOT IMPORT SYNTHETIC PACKAGE')\\n")
asset=package/'tests/final.py';asset.parent.mkdir()
asset.write_text('expected = -4.9275633\\n')
meta=root/'synthetic_tests-0.1.dist-info';meta.mkdir()
(meta/'METADATA').write_text('Name: synthetic-tests\\nVersion: 0.1\\n')
(meta/'RECORD').write_text('synthetic/__init__.py,,\\nsynthetic/tests/final.py,,\\n')
print(json.dumps({'distribution':'synthetic-tests','path':'synthetic/tests/final.py',
 'sha256':hashlib.sha256(asset.read_bytes()).hexdigest(),
 'reason':'Synthetic unused test literal matches final.csv; copy programs never import this package'}))
"""

DENIED = """from pathlib import Path
for name in ('asset-value-hints.json','dependency-assets-final.json'):
 try: Path('/work/construction-inspection',name).read_bytes()
 except PermissionError: pass
 else: raise RuntimeError('Oracle could read private construction evidence')
print('private reads denied')
"""
PRIVACY = (
    "import json\nfrom grading_remote import ORACLE,run_as\n"
    f"print(json.dumps(run_as(ORACLE,['/work/venv/bin/python','-c',{DENIED!r}],"
    "__import__('pathlib').Path('/task'),30)))\n"
)


async def checks(remote, root):
    for name in (
        "materialization_remote.py",
        "grading_remote.py",
        "dependency_assets.py",
        "installed_asset_hints.py",
        "asset_literal_inspection.py",
    ):
        await remote.upload(HERE / name, "/work/" + name)

    async def command(argv, label):
        reply = await remote.command(argv, 60, label)
        if reply["exit_code"] or reply["timed_out"]:
            raise RuntimeError("Synthetic hints control failed: " + json.dumps(reply))
        return reply

    await command(["python", "-c", SETUP], "synthetic-setup")
    await command(["python", "/work/grading_remote.py", "initialize"], "synthetic-roles")
    removal = json.loads(
        (await command(["/work/venv/bin/python", "-c", INSTALLED], "synthetic-installed"))["log"]
    )
    request = {
        "input_paths": ["data.csv"],
        "output_paths": ["final.csv"],
        "derive_code": base.DERIVE,
        "oracle_code": base.ORACLE,
        "original_source": "result = data.copy()\n",
        "seconds": 30,
    }
    observed = []
    for name, files in (("before-removal", []), ("after-removal", [removal])):
        request.update(
            new_dependency_exclusions={"files": files},
            effective_dependency_exclusions={"files": files},
            controlled_execution_deadline=time.time() + 120,
        )
        path = root / (name + "-request.json")
        path.write_text(json.dumps(request, indent=2) + "\n")
        await remote.upload(path, "/work/grading-private/materialization.json")
        result = json.loads(
            (await command(["python", "/work/materialization_remote.py"], name))["log"]
        )
        assert result["status"] == "executed_requires_scientific_validation"
        catalog_path, hints_path = root / (name + "-catalog.json"), root / (name + "-hints.json")
        for target, local, key in (
            ("dependency-assets-final.json", catalog_path, "asset_catalog"),
            ("asset-value-hints.json", hints_path, "asset_value_hints"),
        ):
            await remote.download("/work/grading-private/" + target, local)
            identity = result["environment"][key]
            assert local.stat().st_size == identity["bytes"]
            assert hashlib.sha256(local.read_bytes()).hexdigest() == identity["sha256"]
        hints = json.loads(hints_path.read_text())
        assert hints["source"] == result["environment"]["asset_value_hints"]["source"]
        assert (
            hints["source"]["asset_catalog_sha256"]
            == hashlib.sha256(catalog_path.read_bytes()).hexdigest()
        )
        assert len(hints["findings"]) == (0 if files else 1)
        if not files:
            finding = hints["findings"][0]
            assert finding["path"] == removal["path"]
            assert finding["asset_sha256"] == removal["sha256"]
            assert finding["reference_path"] == "final.csv"
        else:
            assert all(
                result[k] == observed[0][k] for k in ("inputs", "reference", "oracle_outputs")
            )
        read = json.loads(
            (
                await command(
                    [
                        "python",
                        "/work/grading_remote.py",
                        "shell",
                        "author",
                        "cat /work/construction-inspection/asset-value-hints.json",
                        "30",
                    ],
                    name + "-author-read",
                )
            )["log"]
        )
        assert read["exit_code"] == 0
        assert (
            hashlib.sha256(read["stdout"].encode()).hexdigest()
            == hashlib.sha256(hints_path.read_bytes()).hexdigest()
        )
        denied = json.loads(
            (await command(["python", "-c", PRIVACY], name + "-oracle-denial"))["log"]
        )
        assert denied["exit_code"] == 0 and denied["stdout"] == "private reads denied\n"
        assert result["oracle_isolation"]["exit_code"] == 0
        (root / (name + "-result.json")).write_text(json.dumps(result, indent=2) + "\n")
        observed.append(result)
    # A new failed computation must remove the previous visible reports first.
    request.update(
        derive_code="raise SystemExit(7)\n",
        new_dependency_exclusions={"files": []},
        controlled_execution_deadline=time.time() + 120,
    )
    path = root / "failed-fresh-attempt-request.json"
    path.write_text(json.dumps(request, indent=2) + "\n")
    await remote.upload(path, "/work/grading-private/materialization.json")
    failed = json.loads(
        (await command(["python", "/work/materialization_remote.py"], "failed-fresh-attempt"))[
            "log"
        ]
    )
    assert failed["status"] == "incomplete" and failed["derivation"]["exit_code"] == 7
    await command(
        [
            "python",
            "-c",
            "from pathlib import Path\n"
            "assert not any(Path('/work/construction-inspection',name).exists() "
            "for name in ('asset-value-hints.json','dependency-assets-final.json'))\n",
        ],
        "stale-reports-absent",
    )
    (root / "failed-fresh-attempt-result.json").write_text(json.dumps(failed, indent=2) + "\n")
    return [
        {"name": "installed-hints-bound-and-private", "passed": True},
        {"name": "declared-removal-fresh-results-no-hints", "passed": True},
        {"name": "failed-fresh-attempt-invalidates-visible-reports", "passed": True},
    ]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("config", type=Path)
    parser.add_argument("root", type=Path)
    args = parser.parse_args()
    print(
        json.dumps(
            asyncio.run(
                base.base.run(json.loads(args.config.read_text()), args.root, checks=checks)
            )
        )
    )
