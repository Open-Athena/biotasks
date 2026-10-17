"""Run no-model native history controls before an acceptance decision exists."""
import argparse
import asyncio
import os
from pathlib import Path
from history_runtime_input import check_task
from run_pr_provider_preflight import run


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--task', type=Path, required=True)
    parser.add_argument('--input-review', dest='acceptance', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.agents = ['nop', 'oracle']
    os.environ['BIOTASKS21_PROVIDER_MODULE'] = 'history_provider_environment'
    asyncio.run(run(args, validate_task=check_task))


if __name__ == '__main__':
    main()
