"""Run pinned native entity gates on fetched PR2633 source and test revisions.

This is static source selection evidence, not the complete history-worker filter
or a bootstrap/test contrast. Input bytes are hashed for reproducibility.
"""
import argparse
import hashlib
import json
from pathlib import Path
from repo2rlenv.pipelines.recipes.history.selection import check_entities
from repo2rlenv.spec.recipe_options import R2EGymOptions, SWENextOptions


def run(prefix, output):
    root=Path(__file__).resolve().parent
    paths={key:Path(str(prefix)+'-'+key+'.py') for key in ('base-source','head-source','base-tests','head-tests')}
    text={key:p.read_text() for key,p in paths.items()}
    records={}
    for recipe,cls in [('swe-next',SWENextOptions),('r2e-gym',R2EGymOptions)]:
        profile=json.loads((root/(recipe+'-skbio-profile.json')).read_text())
        options=cls.model_validate(profile['options'])
        try:
            selection=check_entities({options.source_paths[0]:(text['base-source'],text['head-source'])},
                                     {options.test_paths[0]:(text['base-tests'],text['head-tests'])},options)
        except ValueError as exc:
            records[recipe]={'status':'entity_filter_rejected','reason':str(exc)}
        else:
            records[recipe]={'status':'entity_filter_passed','selection':selection}
    report={'stage':'static_native_entity_filter_only','base':'71286a24bddff66c82cb25a7ca13441aa13c2f2c',
            'head':'9bbf05b530a9fe08ab200e9c073a118e60096d3c','records':records,
            'input_sha256':{key:hashlib.sha256(p.read_bytes()).hexdigest() for key,p in paths.items()},
            'remaining':['Full changed-path and patch-size selection','Historical snapshot extraction','Native bootstrap and old/new test contrast','GLM issue authoring','Standalone native export/validation'],
            'model_calls':0,'remote_workers':0}
    output.parent.mkdir(parents=True,exist_ok=True);output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(records))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--prefix',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();run(args.prefix,args.output)
