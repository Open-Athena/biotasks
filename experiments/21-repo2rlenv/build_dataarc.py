"""Run the pinned Repo2RLEnv DataArc implementation on a frozen parent cohort.

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
from repo2rlenv.pipelines.recipes.dataarc import recipe
from repo2rlenv.pipelines.recipes.dataarc.pipeline import DataArcPipeline
from repo2rlenv.spec.input import GenerationInput
from repo2rlenv.spec.recipe_options import DataArcOptions


def prepare(spec, manifest, settings):
    options = DataArcOptions.model_validate(manifest['recipes']['dataarc']['options'])
    if (options.target, options.max_candidates, options.max_repairs) != (3, 10, 2):
        raise ValueError('Unexpected candidate or repair bounds')
    pipeline = DataArcPipeline(spec, options)
    seeds = recipe.load_seeds(spec.source.path, options)
    hashes = [hashlib.sha256(json.dumps(x, sort_keys=True).encode()).hexdigest() for x in seeds]
    if hashes != [x['sha256'] for x in manifest['recipes']['dataarc']['records']]:
        raise ValueError('Parent-derived seed records changed')
    if settings['stage'] != 'generation_only' or settings['paid_fallback']:
        raise ValueError('Expected approved generation adaptation')
    if (spec.llm.model != 'glm-5.3' or spec.llm.fallback is not None
            or spec.llm.max_concurrent != 1
            or spec.llm.timeout_sec != settings['request_timeout_sec']):
        raise ValueError('Expected serial free GLM with approved request timeout')
    if not 0 < spec.execution.timeout_sec <= 6900:
        raise ValueError('Execution must leave cleanup time within two hours')
    return pipeline, options


def run(args):
    if os.environ.get('REPO2RLENV_MODEL_WORKER') != '1' or not os.environ.get('IRIS_OUTPUT_DIR'):
        raise RuntimeError('Approved remote controller and output capture required')
    spec = GenerationInput.model_validate_json(args.input.read_text())
    manifest = json.loads(args.manifest.read_text())
    settings = json.loads(args.adaptation.read_text())
    pipeline, options = prepare(spec, manifest, settings)
    output = spec.execution.campaign_dir
    save_record(output / 'dataarc-settings.json', {
        'stage': 'native_materialization_build_repair_trial_export',
        'implementation': 'pinned Repo2RLEnv experimental DataArc implementation',
        'native_supported': pipeline.native_supported,
        'native_options': options.model_dump(mode='json'), 'adaptation': settings,
        'parent_task_id': manifest['parent_task_id'],
        'parent_manifest_sha256': hashlib.sha256(args.manifest.read_bytes()).hexdigest(),
        'context_limits': manifest['dataarc_context_limits'],
        'related_variant_policy': manifest['related_variant_policy'],
        'independent_acceptance': False,
    })
    try:
        with adapted_authoring(settings, output, metering_target='dataarc'):
            result = pipeline.run(Path(spec.output.destination))
        record = dataclasses.asdict(result)
        record['out_dir'] = str(result.out_dir)
        save_record(output / 'dataarc-result.json', record)
    finally:
        preserve(output, Path(os.environ['IRIS_OUTPUT_DIR']))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    for name in ('input', 'manifest', 'adaptation'):
        parser.add_argument('--' + name, type=Path, required=True)
    run(parser.parse_args())
