"""Completed invocation must be inert, including after local duplicate cleanup."""
import argparse
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import controller
from common import sha,write


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--after-cleanup',action='store_true');args=parser.parse_args()
    directory=ROOT/'private/OHIF__Viewers';budget=ROOT.parents[2]/'33/experiments/33-unattended-validation/budget.json'
    paths=sorted(directory.glob('*.json'))+[budget]
    before={str(p):sha(p) for p in paths}
    controller.load_credentials()
    with controller.connect(Path('/home/exedev/projects/marin/lib/iris/config/marin.yaml')) as client:result=controller.run_once(client,budget)
    after={str(p):sha(p) for p in paths}
    assert result=={'state':'complete'} and before==after
    record=dict(state='complete',source_stage_and_budget_files_unchanged=len(paths),before=before,after=after,
        after_local_cleanup=args.after_cleanup,new_submissions=0,model_calls=0)
    write(ROOT/('post-cleanup-reinvoke.json' if args.after_cleanup else 'completed-reinvoke.json'),record)
    print(json.dumps({k:v for k,v in record.items() if k not in ['before','after']}))


if __name__=='__main__':main()
