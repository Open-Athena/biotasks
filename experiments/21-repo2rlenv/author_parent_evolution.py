"""Native SETA Evol design on the prepared parent; no build or acceptance claims."""
import argparse
import hashlib
import json
import os
from pathlib import Path

from glm_authoring_adapter import adapted_authoring
from preserve_author_output import preserve
from repo2rlenv.campaigns.budget import BudgetLedger
from repo2rlenv.execution.lifecycle import save_record
from repo2rlenv.pipelines.recipes.seta_evol import recipe
from repo2rlenv.spec.input import LLMSpec
from repo2rlenv.spec.recipe_options import TaskEvolutionOptions


def run(args):
    assert os.environ.get('REPO2RLENV_MODEL_WORKER')=='1'
    assert os.environ.get('IRIS_OUTPUT_DIR')
    manifest=json.loads(args.manifest.read_text())
    options=TaskEvolutionOptions.model_validate(manifest['recipes']['seta_evol']['options'])
    seeds=recipe.load_parents(args.parent,options)
    hashes=[hashlib.sha256(json.dumps(x,sort_keys=True).encode()).hexdigest() for x in seeds]
    assert hashes==[x['sha256'] for x in manifest['recipes']['seta_evol']['records']]
    assert len(seeds)==3 and options.max_candidates==10
    settings=json.loads(args.adaptation.read_text())
    assert settings['stage']=='generation_only' and not settings['paid_fallback']
    args.output.mkdir(parents=True,exist_ok=False)
    model=LLMSpec(provider='openai',model='glm-5.3',endpoint=os.environ['BIOTASKS21_GLM_ENDPOINT'],
                  api_key_env='BIOTASKS21_GLM_KEY',max_concurrent=1,
                  timeout_sec=settings['request_timeout_sec'],fallback=None)
    ledger=BudgetLedger(args.output/'native-model-reservations.sqlite',limit_usd='8')
    state={'stage':'seta_evol_design_only','parent_bundle_hash':manifest['parent_bundle_hash'],
           'records':[],'built_tasks':0,'independently_accepted_tasks':0}
    save_record(args.output/'settings.json',{'generation_settings':settings,'native_options':options.model_dump(mode='json'),
                'max_design_requests':3,'native_design_max_tokens':9000,'parent_manifest_sha256':hashlib.sha256(args.manifest.read_bytes()).hexdigest()})
    try:
        with adapted_authoring(settings,args.output,metering_target='seta_evol'):
            for seed,digest in zip(seeds,hashes,strict=True):
                record={'seed_sha256':digest,'title':seed['title'],'status':'dispatched'}
                state['records'].append(record);save_record(args.output/'designs.json',state)
                try:
                    design=recipe.design(seed,model=model,ledger=ledger,receipt=args.output/'models'/(digest+'.json'),
                                         operation_id='seta-evol-design:'+digest,resume=False)
                    record.update(status='filtered' if design.filtered_reason else 'designed',design=design.model_dump(mode='json'))
                except Exception as exc:
                    record.update(status='failed',error_type=type(exc).__name__)
                save_record(args.output/'designs.json',state)
    finally:
        preserve(args.output,Path(os.environ['IRIS_OUTPUT_DIR']))


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    for name in ('parent','manifest','adaptation','output'):
        parser.add_argument('--'+name,type=Path,required=True)
    run(parser.parse_args())
