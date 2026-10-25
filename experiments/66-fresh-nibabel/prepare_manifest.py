"""Bind declared NiBabel inputs to the existing qualified installed runtime."""
import json
from pathlib import Path
from biotasks.validation.files import inventory, json_sha, sha
from biotasks.generation import resources

root = Path(__file__).resolve().parent
old = root.parents[2] / '62/experiments/62-fresh-dendropy'
value = json.loads((old / 'manifest.json').read_text())
assert json.loads((root / 'client-profile.json').read_text()) == value['client_profile']
assert resources.code_identity() == 'e5b76b84328bc892fb63640fb07f9fbb16f7ae5b83a6045f335b387673d23940'

def ref(name):
    path = root / name
    return {'path': str(path), 'sha256': sha(path)}

value.update(id='issue66', price_quote=ref('price-quote.json'), archive={'kind': 'hf-public', 'bucket': 'open-athena/biotasks', 'prefix': 'research/66-fresh-nibabel'})
value['cases'] = [dict(
    id='nibabel', run_id='biotasks66-nibabel-001', mode='fresh',
    native_config=ref('native-config.json'), candidates=ref('candidates.json'),
    notices={'path': str(root / 'notices'), 'inventory_sha256': json_sha(inventory(root / 'notices'))},
    publication={'eligible': True, 'review': 'Public pinned NiBabel COPYING at bootstrap and exact PR base/head plus changed Python source/test headers and original upstream notices retained. NiBabel MIT terms and explicitly separate third-party/data notices, including PAR/REC PDDL terms; not blanket MIT. No changed data files. Bounded text task/cache/model/native observations and own metadata only, no environments/images/biological datasets/media/credentials. Existing bounded text/decoded-observation/credential eligibility checks apply; unknown publication eligibility remains a hold. Same declared upstream boolean option and generic targeting, unchanged tests/parser/reward/deadlines/resources, no per-task dependency or installation repair. Original applicable terms and attribution retained; research archival, not dataset/training release.'},
    targeting_policy='workspace-python-v1')]
(root / 'manifest.json').write_text(json.dumps(value, indent=2) + '\n')
