"""Freeze the native sampler output and an explicit biological-input selection."""
import hashlib
import json
from pathlib import Path
from repo2rlenv.pipelines.recipes.tmax.sampler import sample_inputs, template_prompt

root=Path(__file__).resolve().parent
seed=root/'seeds/tmax-biological-v1'
records=sample_inputs(seed/'sampler.json')
assert records==sample_inputs(seed/'sampler.json')
selected=[];decisions=[]
for record in records:
    reason=[]
    if record['scenario']=='bioinformatics analyst processing sequences':reason.append('explicit bioinformatics scenario')
    if 'Bioinformatics format parsing (FASTA, PDB)' in record['primitive_skills']:reason.append('explicit biological format parsing')
    decisions.append({'draw':record['draw'],'selected':bool(reason),'reason':reason or ['no explicit biological context'],
                      'record_sha256':hashlib.sha256(json.dumps(record,sort_keys=True).encode()).hexdigest()})
    if reason:
        assert 'Scientific Computing' in template_prompt(record)
        selected.append(record)
assert len(records)==10 and len(selected)==3
for name,value in [('native-samples.json',records),('selected-inputs.json',selected),('selection.json',decisions)]:
    (seed/name).write_text(json.dumps(value,indent=2)+'\n')
manifest={
    'stage':'input_selection_prepared_unexecuted', 'recipe':'tmax',
    'repo2rlenv_revision':'27d04ee8203cd5b2f20c3997d13836e5f5b64238',
    'cohort':'tmax-biological-v1','native_samples':10,'selected_inputs':3,
    'selection_rule':'Retain explicit bioinformatics scenario or FASTA/PDB format-parsing skill from native scientific-computing/Python sampler; no seed search or record rewriting.',
    'selection_intervention':'Run the native designer/materializer on these selected records; the unmodified pipeline would consume all ten sampler records.',
    'options':{'target':3,'max_candidates':10,'max_repairs':2},
    'biological_provenance':'Taxonomy-only seed descriptions; no observed biological data. Generated fixtures must be classified and independently reviewed before acceptance.',
    'files':{name:hashlib.sha256((seed/name).read_bytes()).hexdigest() for name in ['sampler.json','native-samples.json','selected-inputs.json','selection.json']},
    'limitations':['Biological intent in a seed does not establish biological content of a generated task.','All sampler-selected skills remain intact, including non-biological numerical or infrastructure skills.','No design calls, environment builds, exports, acceptance or solver trials yet.']}
(seed/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(json.dumps({'native_samples':10,'selected_draws':[r['draw'] for r in selected],'repeatable':True,'model_calls':0}))
