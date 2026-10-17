"""Freeze native Endless Terminals draws and explicit synthetic biology contexts."""
import argparse
import hashlib
import json
from importlib.resources import files
from pathlib import Path
from repo2rlenv.pipelines.recipes.endless_terminals.sampler import sample_inputs

CONTEXTS = (
    'A bioinformatics analyst validates synthetic BED genomic interval files: check chromosome/start/end columns, retain zero-based half-open coordinates, and produce an explicitly specified valid-record and rejected-record report.',
    'A bioinformatics analyst reconciles synthetic genomic interval annotations with a synthetic sample metadata TSV: preserve identifiers, expose unmatched records, and write a deterministic summary with an explicitly specified schema.',
    'A bioinformatics analyst summarizes synthetic genomic interval coverage across named samples: define overlap and interval-length semantics explicitly and produce a deterministic tabular output from tiny local fixtures.',
)


def prepare(output):
    output.mkdir(parents=True, exist_ok=False)
    sampler = {'count':10, 'seed':24, 'categories':['data transformation','CSV/JSON data manipulation','text processing and manipulation']}
    (output/'sampler.json').write_text(json.dumps(sampler,indent=2)+'\n')
    native = sample_inputs(output/'sampler.json')
    adapted = []
    for index, row in enumerate(native):
        context = CONTEXTS[index % len(CONTEXTS)]
        candidate = dict(row)
        candidate['scenario'] = context
        candidate['request'] = (row['request'] + '\nExplicit biological-context adaptation: ' + context +
            ' Use only small synthetic local data created for this task; identify it as synthetic.'
            ' No external dataset, account, network service, or accelerator is required.'
            ' Preserve the sampled category and complexity when defining the task.')
        candidate['biological_context_intervention'] = True
        candidate['native_scenario'] = row['scenario']
        adapted.append(candidate)
    (output/'native-samples.json').write_text(json.dumps(native,indent=2)+'\n')
    (output/'adapted-inputs.json').write_text(json.dumps(adapted,indent=2)+'\n')
    taxonomy = files('repo2rlenv.pipelines.recipes.endless_terminals').joinpath('taxonomy.json').read_bytes()
    manifest = {'stage':'prepared_not_executed','cohort':'endless-synthetic-genomic-intervals-v1',
                'generator_revision':'27d04ee8203cd5b2f20c3997d13836e5f5b64238',
                'native_taxonomy_sha256':hashlib.sha256(taxonomy).hexdigest(),
                'native_sampler_settings':sampler,'candidate_count':len(adapted),
                'target_independently_validated':3,'max_candidates':10,'max_repairs':2,
                'input_provenance':'Original synthetic biological contexts authored for this experiment; sampled native category/complexity retained.',
                'baseline_finding':'Native taxonomy has no explicit biology scenario; general researcher/data-analysis contexts do not establish biological provenance.',
                'intervention':'Replace scenario and append explicit biological context to each native sampled request; no recipe authoring or grader logic changed.',
                'lineage':'One synthetic genomic-interval cohort, overlapping domain with SETA interval seeds but not sourced from their generated tasks.',
                'model_calls':0,'remote_workers':0,'options':{'target':3,'max_candidates':10,'max_repairs':2},
                'files':{name:hashlib.sha256((output/name).read_bytes()).hexdigest() for name in ['sampler.json','native-samples.json','adapted-inputs.json']}}
    (output/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    assert sample_inputs(output/'sampler.json') == native
    assert len(adapted)==10 and all(x['category']==y['category'] and x['task_complexity']==y['task_complexity'] for x,y in zip(native,adapted,strict=True))
    return manifest


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    print(json.dumps(prepare(args.output)))
