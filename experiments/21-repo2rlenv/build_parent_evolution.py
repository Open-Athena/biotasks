"""Run the pinned Repo2RLEnv SETA Evol implementation on a frozen parent cohort.

Requires an already provisioned remote worker. Allocation, deadline enforcement,
remote evidence recovery, and cleanup belong to the enclosing controller.
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
from repo2rlenv.pipelines.recipes.seta_evol import recipe
from repo2rlenv.pipelines.task_evolve import TaskEvolutionPipeline
from repo2rlenv.pipelines.recipes.terminal.runner import run_synthesis
from replay_parent_evolution import saved_designer
from repo2rlenv.spec.input import GenerationInput
from repo2rlenv.spec.recipe_options import TaskEvolutionOptions


def prepare(spec, manifest, settings, designs, designs_sha256):
    options = TaskEvolutionOptions.model_validate(manifest['recipes']['seta_evol']['options'])
    if (options.target, options.max_candidates, options.max_repairs) != (3, 10, 2):
        raise ValueError('Unexpected candidate or repair bounds')
    pipeline = TaskEvolutionPipeline(spec, options)
    seeds = recipe.load_parents(spec.source.path, options)
    hashes = [hashlib.sha256(json.dumps(x, sort_keys=True).encode()).hexdigest() for x in seeds]
    if hashes != [x['sha256'] for x in manifest['recipes']['seta_evol']['records']]:
        raise ValueError('Parent-derived seed records changed')
    if settings['stage'] != 'generation_only' or settings['paid_fallback']:
        raise ValueError('Expected approved generation adaptation')
    if (spec.llm.model != 'glm-5.3' or spec.llm.fallback is not None
            or spec.llm.max_concurrent != 1
            or spec.llm.timeout_sec != settings['request_timeout_sec']):
        raise ValueError('Expected serial free GLM with approved request timeout')
    if not 0 < spec.execution.timeout_sec <= 6900:
        raise ValueError('Execution must leave cleanup time within two hours')
    designer = saved_designer(designs, designs_sha256)
    return pipeline, options, seeds, designer


def run(args):
    if os.environ.get('REPO2RLENV_MODEL_WORKER') != '1' or not os.environ.get('IRIS_OUTPUT_DIR'):
        raise RuntimeError('Approved remote controller and output capture required')
    spec = GenerationInput.model_validate_json(args.input.read_text())
    manifest = json.loads(args.manifest.read_text())
    settings = json.loads(args.adaptation.read_text())
    pipeline, options, seeds, designer = prepare(spec, manifest, settings, args.designs, args.designs_sha256)
    output = spec.execution.campaign_dir
    save_record(output / 'seta_evol-settings.json', {
        'stage': 'native_materialization_build_repair_trial_export',
        'implementation': 'pinned Repo2RLEnv experimental SETA Evol implementation',
        'native_supported': pipeline.native_supported,
        'native_options': options.model_dump(mode='json'), 'adaptation': settings,
        'parent_task_id': manifest['parent_task_id'],
        'parent_manifest_sha256': hashlib.sha256(args.manifest.read_bytes()).hexdigest(),
        'saved_designs_sha256': args.designs_sha256, 'new_design_calls': 0,
        'related_variant_policy': manifest['related_variant_policy'],
        'independent_acceptance': False,
    })
    try:
        with adapted_authoring(settings, output, metering_target='terminal_builder'):
            result = run_synthesis(spec, options, Path(spec.output.destination), pipeline.on_event,
                                   inputs=seeds, designer=designer, builder_prompt=recipe.builder_prompt())
        record = dataclasses.asdict(result)
        record['out_dir'] = str(result.out_dir)
        save_record(output / 'seta_evol-result.json', record)
    finally:
        preserve(output, Path(os.environ['IRIS_OUTPUT_DIR']))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    for name in ('input', 'manifest', 'adaptation', 'designs'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--designs-sha256', required=True)
    run(parser.parse_args())
