"""Check exact replay and retained failure against the native parent loader."""
import hashlib
import json
import tempfile
from pathlib import Path
from replay_parent_evolution import saved_designer
from repo2rlenv.pipelines.recipes.seta_evol import recipe
from repo2rlenv.spec.recipe_options import TaskEvolutionOptions

root=Path(__file__).resolve().parent
source=root/'evidence/parent-evolution-design-01/designs.json'
raw=source.read_bytes();digest=hashlib.sha256(raw).hexdigest();payload=json.loads(raw)
manifest=json.loads((root/'seeds/pr2633-parent-v1/manifest.json').read_text())
options=TaskEvolutionOptions.model_validate(manifest['recipes']['seta_evol']['options'])
seeds=recipe.load_parents(root/'seeds/pr2633-parent-v1/parent',options)
designer=saved_designer(source,digest)
with tempfile.TemporaryDirectory() as temp:
    temp=Path(temp)
    for index,(seed,row) in enumerate(zip(seeds,payload['records'],strict=True)):
        try:
            result=designer(seed,model=None,ledger=None,receipt=temp/f'{index}.json',operation_id='fixture',resume=False)
        except ValueError:
            assert row['status']=='failed'
        else:
            assert result.model_dump(mode='json')==row['design']
        assert json.loads((temp/f'{index}.json').read_text())['model_calls']==0
    altered=dict(seeds[0],title='changed')
    try:designer(altered,model=None,ledger=None,receipt=temp/'changed.json',operation_id='fixture',resume=False)
    except ValueError:pass
    else:raise AssertionError('Changed seed accepted')
    try:saved_designer(source,'0'*64)
    except ValueError:pass
    else:raise AssertionError('Changed evidence accepted')
print('PASS: two designs preserved exactly; original failed design remains failed; altered seeds and evidence rejected; zero model calls.')
