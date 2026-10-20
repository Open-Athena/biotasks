"""Audit binary blind trials against the exact frozen expected test identities.

Reads retained evidence and restored original inputs only. It does not run the
target, call a model, fix a task, or establish public preservation/cleanup.
"""

import argparse
import json
import xml.etree.ElementTree as ET
from pathlib import Path

from harbor.models.task.task import Task

from audit_authored_blind_batch import audit_authored


def run(recovered, inputs, manifest):
    result = audit_authored(recovered, inputs, manifest, lambda task: Task(task).checksum)
    identities = []
    for item in manifest["units"]:
        unit = item["unit"]
        task = inputs / unit / "task"
        contract = json.loads((task / "tests/contract.json").read_text())
        expected = set(contract["expected_passes"])
        for name in ("nop", "oracle", "glm-blind-01"):
            trial = recovered / unit / "native-trial/trials" / name
            state = json.loads((trial / "verifier/result.json").read_text())
            statuses = {}
            for case in ET.parse(trial / "verifier/results.xml").iter("testcase"):
                identity = case.attrib["classname"] + "::" + case.attrib["name"]
                assert identity not in statuses
                statuses[identity] = (
                    "error" if case.find("error") is not None else
                    "failed" if case.find("failure") is not None else
                    "skipped" if case.find("skipped") is not None else "passed"
                )
            assert set(statuses) == expected and statuses == state["statuses"]
            identities.append({"unit": unit, "trial": name,
                               "exact_expected_identities": len(expected),
                               "junit_statuses_match_native_result": True})
    result["expected_test_identity_recomputation"] = identities
    result["original_task_assets_restored_and_verified"] = sum(
        item["asset_count"] for item in manifest["units"]
    )
    result["task_specific_fixes"] = 0
    result["original_runtime_assets_changed"] = False
    result["trial_batch_elapsed_seconds"] = json.loads(
        (recovered / "batch-status.json").read_text()
    )["elapsed_seconds"]
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    for name in ("recovered", "inputs", "manifest", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    report = run(args.recovered, args.inputs, json.loads(args.manifest.read_text()))
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"blind_attempts": report["blind_attempts_observed"],
                      "scored": report["scored_blind_attempts"],
                      "exact_contract_checks": len(report["expected_test_identity_recomputation"])}))
