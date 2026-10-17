"""Run native history selection/contrast/authoring/export on a supplied worker.

The enclosing controller owns allocation, deadlines, remote evidence and cleanup.
Frozen SWE-gen PR metadata uses the native cache path; no remote GitHub key.
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
from repo2rlenv.pipelines.pr_to_env import PRToEnvPipeline
from repo2rlenv.spec.input import GenerationInput, PRSource
from repo2rlenv.spec.recipe_options import PRRecipeOptions


def prepare(spec, profile, settings, source, source_sha256):
    options = PRRecipeOptions.model_validate(profile['options'])
    if profile['recipe'] != 'swe_gen' or spec.pipeline.recipe != 'swe_gen':
        raise ValueError('Unexpected recipe')
    if spec.source != PRSource.model_validate(profile['source']):
        raise ValueError('Input and frozen source profile disagree')
    if options.target != 3 or options.max_candidates != 10:
        raise ValueError('Unexpected candidate limits')
    if settings['stage'] != 'generation_only' or settings['paid_fallback']:
        raise ValueError('Unexpected generation adaptation')
    if spec.llm.model != 'glm-5.3' or spec.llm.fallback is not None or spec.llm.max_concurrent != 1 or spec.llm.timeout_sec != 1200:
        raise ValueError('Expected serial free GLM')
    if spec.pipeline.name != PRToEnvPipeline.name or not 0 < spec.execution.timeout_sec <= 6900:
        raise ValueError('Pipeline or execution deadline mismatch')
    raw = source.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if digest != source_sha256 or digest != profile['source_sha256']:
        raise ValueError('Frozen source changed')
    record = json.loads(raw)
    if spec.source.urls != [record['url']] or not record.get('head') or not record.get('source_diff'):
        raise ValueError('Frozen source does not match selected PR')
    if record['source_files'] != options.source_paths or record['test_files'] != options.test_paths:
        raise ValueError('Frozen source paths differ from profile')
    cache = spec.execution.campaign_dir / 'runs' / spec.execution.run_id / 'candidates' / hashlib.sha256(record['url'].encode()).hexdigest()[:20] / 'source.json'
    save_record(cache, record)
    return PRToEnvPipeline(spec, options), options


def run(args):
    if os.environ.get('REPO2RLENV_MODEL_WORKER')!='1' or not os.environ.get('IRIS_OUTPUT_DIR'):
        raise RuntimeError('Approved remote controller and capture directory required')
    spec=GenerationInput.model_validate_json(args.input.read_text())
    profile=json.loads(args.profile.read_text());settings=json.loads(args.adaptation.read_text())
    pipeline,options=prepare(spec,profile,settings,args.source,args.source_sha256)
    output=spec.execution.campaign_dir
    save_record(output/'swe-gen-settings.json',{'profile':profile,'adaptation':settings,
        'native_options':options.model_dump(mode='json'),'source_sha256':args.source_sha256,
        'independently_accepted_tasks':0,'blind_solver_attempts':0})
    try:
        with adapted_authoring(settings,output,metering_target='swe_gen'):
            result=pipeline.run(Path(spec.output.destination))
        record=dataclasses.asdict(result);record['out_dir']=str(result.out_dir)
        save_record(output/'swe-gen-result.json',record)
    finally:
        # Streaming archive; full source contexts are retained, not silently pruned.
        preserve(output,Path(os.environ['IRIS_OUTPUT_DIR']),max_bytes=2*1024**3)


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    for name in ('input','profile','adaptation'):parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--source',type=Path);parser.add_argument('--source-sha256')
    run(parser.parse_args())
