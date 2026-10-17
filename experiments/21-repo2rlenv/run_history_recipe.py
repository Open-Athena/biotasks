"""Run native history selection/contrast/authoring/export on a supplied worker.

The enclosing controller owns allocation, deadlines, remote evidence and cleanup.
Frozen SWE-Next PR metadata uses the native cache path; no remote GitHub key.
"""
import argparse
import dataclasses
import hashlib
import json
import os
from pathlib import Path
from glm_authoring_adapter import adapted_authoring
from preserve_author_output import preserve
from repo2rlenv.execution.lifecycle import save_record
from repo2rlenv.pipelines.recipes.swe_next.pipeline import SWENextPipeline
from repo2rlenv.pipelines.recipes.r2e_gym.pipeline import R2EGymPipeline
from repo2rlenv.spec.input import GenerationInput, RepoSpec
from repo2rlenv.spec.recipe_options import SWENextOptions, R2EGymOptions


def prepare(spec, profile, settings, pulls=None, pulls_sha256=None):
    recipe=profile['recipe']
    cls,option_cls={'swe_next':(SWENextPipeline,SWENextOptions),
                    'r2e_gym':(R2EGymPipeline,R2EGymOptions)}[recipe]
    options=option_cls.model_validate(profile['options'])
    if spec.pipeline.recipe!=recipe or spec.repo!=RepoSpec.model_validate(profile['repo']):
        raise ValueError('Input and frozen profile disagree')
    if options.target!=3 or options.max_candidates!=10:
        raise ValueError('Unexpected candidate limits')
    if settings['stage']!='generation_only' or settings['paid_fallback']:
        raise ValueError('Unexpected generation adaptation')
    if spec.llm.model!='glm-5.3' or spec.llm.fallback is not None or spec.llm.max_concurrent!=1 or spec.llm.timeout_sec!=1200:
        raise ValueError('Expected serial free GLM')
    if spec.pipeline.name!=cls.name or not 0<spec.execution.timeout_sec<=6900:
        raise ValueError('Pipeline or execution deadline mismatch')
    pipeline=cls(spec,options)
    if recipe=='swe_next':
        raw=pulls.read_bytes()
        if hashlib.sha256(raw).hexdigest()!=pulls_sha256:
            raise ValueError('Frozen PR context changed')
        rows=json.loads(raw)
        if [x['number'] for x in rows]!=options.pr_numbers or any(not x['merged_at'] for x in rows):
            raise ValueError('PR selection differs from frozen profile')
        save_record(spec.execution.campaign_dir/'runs'/spec.execution.run_id/'pulls.json',rows)
    return pipeline,options


def run(args):
    if os.environ.get('REPO2RLENV_MODEL_WORKER')!='1' or not os.environ.get('IRIS_OUTPUT_DIR'):
        raise RuntimeError('Approved remote controller and capture directory required')
    spec=GenerationInput.model_validate_json(args.input.read_text())
    profile=json.loads(args.profile.read_text());settings=json.loads(args.adaptation.read_text())
    pipeline,options=prepare(spec,profile,settings,args.pulls,args.pulls_sha256)
    output=spec.execution.campaign_dir
    save_record(output/'history-settings.json',{'profile':profile,'adaptation':settings,
        'native_options':options.model_dump(mode='json'),'pulls_sha256':args.pulls_sha256,
        'independently_accepted_tasks':0,'blind_solver_attempts':0})
    try:
        with adapted_authoring(settings,output,metering_target='history'):
            result=pipeline.run(Path(spec.output.destination))
        record=dataclasses.asdict(result);record['out_dir']=str(result.out_dir)
        save_record(output/'history-result.json',record)
    finally:
        # Streaming archive; full source contexts are retained, not silently pruned.
        preserve(output,Path(os.environ['IRIS_OUTPUT_DIR']),max_bytes=2*1024**3)


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    for name in ('input','profile','adaptation'):parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--pulls',type=Path);parser.add_argument('--pulls-sha256')
    run(parser.parse_args())
