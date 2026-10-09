"""Read-only interface checks for bounded authoring workers, not acceptance."""

import argparse
import json
from pathlib import Path

from biotasks.factory_native import candidate_hash, native_plan
from biotasks.factory_proposal import proposal_action


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", choices=["specification", "construction"], required=True)
    parser.add_argument("--workspace", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.stage == "specification":
            result = {"status": "proposal_shape_valid", "action": proposal_action(args.workspace)}
        else:
            plan = native_plan(args.workspace)
            result = {
                "status": "package_shape_valid",
                "candidate_sha256": candidate_hash(args.workspace),
                "native_case_count": len(plan["cases"]),
            }
    except (OSError, ValueError, TypeError, KeyError, AttributeError) as error:
        print(json.dumps({"status": "invalid", "reason": str(error)}))
        return 1
    print(json.dumps(result | {"scientific_acceptance": False, "native_execution": False}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
