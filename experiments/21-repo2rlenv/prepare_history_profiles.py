"""Prepare native history-recipe profiles; no clone, build or model execution."""
import json
from pathlib import Path
from repo2rlenv.spec.recipe_options import PythonRepositoryProfile, R2EGymOptions, SWENextOptions

root=Path(__file__).resolve().parent
base=json.loads((root/'r2e-skbio-worker.json').read_text())
pull=json.loads((root/'evidence/history-profile-preparation/pr2633.json').read_text())
assert pull['number']==2633 and pull['merged_at']
profile={k:v for k,v in base['options'].items() if k in PythonRepositoryProfile.model_fields}
profile.update(source_paths=['skbio/stats/composition/_ancombc.py'],
               test_paths=['skbio/stats/composition/tests/test_ancombc.py'])
common=dict(profile,target=3,max_candidates=10,history_limit=2000)
for name,cls,extra in [('swe_next',SWENextOptions,{'pr_numbers':[2633]}),('r2e_gym',R2EGymOptions,{})]:
    options=cls.model_validate({**common,**extra})
    record={'stage':'profile_prepared_unexecuted','recipe':name,
            'repo':{'url':'https://github.com/scikit-bio/scikit-bio','ref':pull['merge_commit_sha'],'access':'public'},
            'options':options.model_dump(mode='json'),
            'provenance':'Frozen PR2633 history calibration; shares lineage with prior PR-runtime task, not a new independent problem.',
            'limitations':['Native source/entity filters, snapshot creation and bootstrap remain unexecuted',
                           'SWE-Next initial calibration has one selected PR; additional independent PRs are needed to reach target three',
                           'R2E-Gym retains native bug-edit/test-match constraints and a bounded history scan',
                           'Instruction authoring must use existing free GLM and explicit approved generation adaptation',
                           'No claim of native Harbor export, independent acceptance or solver result'],
            'model_calls':0,'worker_created':False}
    (root/(name.replace('_','-')+'-skbio-profile.json')).write_text(json.dumps(record,indent=2)+'\n')
print('Prepared native SWE-Next and R2E-Gym options; no live execution.')
