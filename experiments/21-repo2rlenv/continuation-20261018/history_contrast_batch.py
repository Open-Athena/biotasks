"""Run bounded native R2E-Gym selection and contrasts without author/model calls.

Native selection and per-candidate evidence remain untouched in subdirectories.
The root generation record is a derived summary for separate saved-input authoring.
"""

import argparse
import json
import os
import subprocess
from pathlib import Path


def run_batch(config, output, prepare, evaluate):
    if config.get('recipe') != 'r2e_gym':
        raise ValueError('Only the frozen R2E-Gym route is supported')
    options = config['options']
    # Native max_candidates limits eligible selections, not rejected heads.
    # Bounding the history scan also bounds every examined candidate here.
    if not 1 <= options['history_limit'] <= options['max_candidates'] <= 10:
        raise ValueError('History scan must fit the charged candidate allowance')
    if not 1 <= options['target'] <= options['max_candidates']:
        raise ValueError('Invalid batch target')
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    result = {
        'stage': 'selection_started', 'recipe': 'r2e_gym', 'model_calls': 0,
        'attempted': None, 'candidates': [], 'rejected': [],
        'selected_not_evaluated': [], 'independently_admitted': 0,
        'native_selection_source': 'selection/generation.json',
    }
    try:
        selected = prepare(config, output / 'selection')
        candidates = selected['candidates']
        rejected = selected['rejected']
        if selected['attempted'] != len(candidates) + len(rejected):
            raise ValueError('Native selection counter disagreement')
        if selected['attempted'] > options['history_limit']:
            raise ValueError('Native selection exceeded the frozen history bound')
        identities = [c['id'] for c in candidates]
        if len(set(identities)) != len(identities):
            raise ValueError('Repeated native candidate identity')
        if any(not identity or any(c not in '0123456789abcdef' for c in identity)
               for identity in identities):
            raise ValueError('Unexpected native candidate path component')
        result.update(
            stage='contrasts_started', attempted=selected['attempted'],
            repo_revision=selected['repo_revision'],
            rejected=[{'stage': 'native_source_filter', **row} for row in rejected],
            selected_not_evaluated=list(identities),
        )
        for candidate in candidates:
            if len(result['candidates']) >= options['target']:
                break
            identity = candidate['id']
            try:
                evaluated = evaluate({
                    'mode': 'evaluate', 'recipe': config['recipe'],
                    'candidate': candidate, 'options': options,
                    'repository_cache': selected['repository_cache'],
                }, output / 'candidates' / identity)
            except (ValueError, RuntimeError, subprocess.CalledProcessError,
                    subprocess.TimeoutExpired) as exc:
                result['rejected'].append({
                    'id': identity, 'head': candidate['head'],
                    'stage': 'native_contrast_failed', 'error_type': type(exc).__name__,
                    'evidence_directory': 'candidates/' + identity,
                })
            else:
                if evaluated['id'] != identity:
                    raise ValueError('Native contrast returned a different identity')
                result['candidates'].append(evaluated)
            result['selected_not_evaluated'].remove(identity)
        result['stage'] = 'native_contrasts_completed_not_admission'
        return result
    finally:
        (output / 'generation.json').write_text(json.dumps(result, indent=2) + '\n')


def main():
    if os.environ.get('REPO2RLENV_REMOTE_WORKER') != '1':
        raise RuntimeError('Repository execution is remote only')
    from repo2rlenv.pipelines.recipes.history.worker import evaluate, prepare

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('config', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    result = run_batch(json.loads(args.config.read_text()), args.output, prepare, evaluate)
    print(json.dumps({k: result[k] for k in ('stage', 'attempted', 'model_calls')}))


if __name__ == '__main__':
    main()
