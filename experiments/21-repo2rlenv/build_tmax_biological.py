"""Native TMax stages with an explicit frozen biological-input selection."""
import argparse
import dataclasses
import hashlib
import json
import os
from pathlib import Path

from glm_authoring_adapter import adapted_authoring
from preserve_author_output import preserve
from repo2rlenv.execution.lifecycle import save_record
from repo2rlenv.pipelines.recipes.terminal.preflight import initial_state
from repo2rlenv.pipelines.recipes.terminal.runner import run_synthesis
from repo2rlenv.pipelines.recipes.tmax import recipe
from repo2rlenv.pipelines.recipes.tmax.pipeline import TMaxPipeline
from repo2rlenv.pipelines.recipes.tmax.sampler import sample_inputs
from repo2rlenv.spec.input import GenerationInput
from repo2rlenv.spec.recipe_options import TerminalSynthesisOptions


def prepare(spec, manifest_path, settings):
    manifest=json.loads(manifest_path.read_text())
    for name,digest in manifest['files'].items():
        if hashlib.sha256((manifest_path.parent/name).read_bytes()).hexdigest()!=digest:
            raise ValueError('Frozen TMax input changed')
    if Path(spec.source.path).resolve()!=(manifest_path.parent/'sampler.json').resolve():
        raise ValueError('Unexpected sampler source')
    sampled=sample_inputs(spec.source.path)
    original=json.loads((manifest_path.parent/'native-samples.json').read_text())
    selected=json.loads((manifest_path.parent/'selected-inputs.json').read_text())
    if sampled!=original or selected!=[r for r in original if r['scenario']=='bioinformatics analyst processing sequences' or 'Bioinformatics format parsing (FASTA, PDB)' in r['primitive_skills']]:
        raise ValueError('Sampler or selection differs from frozen rule')
    options=TerminalSynthesisOptions.model_validate(manifest['options'])
    if (options.target,options.max_candidates,options.max_repairs)!=(3,10,2):
        raise ValueError('Unexpected candidate bounds')
    if settings['stage']!='generation_only' or settings['paid_fallback']:
        raise ValueError('Unexpected adaptation')
    if spec.llm.model!='glm-5.3' or spec.llm.fallback is not None or spec.llm.max_concurrent!=1 or spec.llm.timeout_sec!=1200:
        raise ValueError('Expected serial free GLM')
    if not 0<spec.execution.timeout_sec<=6900:
        raise ValueError('Expected bounded remote execution')
    return TMaxPipeline(spec,options),options,selected,manifest


def run(args):
    if os.environ.get('REPO2RLENV_MODEL_WORKER')!='1' or not os.environ.get('IRIS_OUTPUT_DIR'):
        raise RuntimeError('Approved remote controller and evidence capture required')
    spec=GenerationInput.model_validate_json(args.input.read_text())
    settings=json.loads(args.adaptation.read_text())
    pipeline,options,selected,manifest=prepare(spec,args.manifest,settings)
    output=spec.execution.campaign_dir
    save_record(output/'tmax-settings.json',{'manifest':manifest,'adaptation':settings,
        'native_options':options.model_dump(mode='json'),'input_selection_intervention':True,
        'independently_accepted_tasks':0})
    try:
        with adapted_authoring(settings,output,metering_target='terminal_stages'):
            result=run_synthesis(spec,options,Path(spec.output.destination),pipeline.on_event,
                inputs=selected,designer=recipe.design,builder_prompt=recipe.builder_prompt(),
                preflight=initial_state,agent_user='user')
        record=dataclasses.asdict(result);record['out_dir']=str(result.out_dir)
        save_record(output/'tmax-result.json',record)
    finally:
        preserve(output,Path(os.environ['IRIS_OUTPUT_DIR']))


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    for name in ('input','manifest','adaptation'):parser.add_argument('--'+name,type=Path,required=True)
    run(parser.parse_args())
