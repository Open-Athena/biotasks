"""Load the frozen factory package before importing the remote seed executor."""

import argparse
import runpy
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check-imports", action="store_true")
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    runtime = root / "factory-runtime.zip"
    if not runtime.is_file():
        raise FileNotFoundError("Frozen factory runtime archive is missing")
    sys.path.insert(0, str(runtime))
    runpy.run_path(
        str(root / "seed_pipeline_worker.py"),
        run_name="_biotasks_import_check" if args.check_imports else "__main__",
    )
    if args.check_imports:
        print("Frozen factory imports passed; no pipeline stages executed")


if __name__ == "__main__":
    main()
