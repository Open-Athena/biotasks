"""Resolve native public PR source and validate the first SWE-gen profile.

Requires authenticated GitHub CLI reads; makes no model or worker calls.
"""
import hashlib,json,inspect
from pathlib import Path
from repo2rlenv.spec.input import PRSource
from repo2rlenv.spec.recipe_options import PRRecipeOptions
from repo2rlenv.pipelines.recipes.swe_gen.source import fetch_source
p=Path(__file__).resolve().parent;base=json.loads((p/'swe-next-skbio-profile.json').read_text())
options=PRRecipeOptions.model_validate({k:v for k,v in base['options'].items() if k in PRRecipeOptions.model_fields})
assert options.target==3 and options.max_candidates==10 and not options.force_generate_instruction
url='https://github.com/scikit-bio/scikit-bio/pull/2633';source=fetch_source(url,options)
assert source['head']=='4c07596c68e8e6c1f51f5ea917e642e933802aa7'
assert source['source_files']==['skbio/stats/composition/_ancombc.py']
assert source['test_files']==['skbio/stats/composition/tests/test_ancombc.py']
out=p/'evidence/swe-gen-skbio-preparation';out.mkdir(exist_ok=True);raw=(json.dumps(source,indent=2)+'\n').encode();(out/'source.json').write_bytes(raw)
profile={'stage':'native_source_resolved_execution_pending','recipe':'swe_gen','source':{'kind':'pr','urls':[url]},'options':options.model_dump(mode='json'),'source_sha256':hashlib.sha256(raw).hexdigest(),'lineage':'PR2633 same underlying problem as PR-runtime/history routes','limitations':['One selected PR; target three cannot be met from this initial calibration alone','Native healthy-head bootstrap, reverse patch, contrast, authoring and export remain unexecuted','Existing free GLM adaptation only when native instruction route calls a model; force_generate_instruction retains native false default']}
PRSource.model_validate(profile['source'])
(p/'swe-gen-skbio-profile.json').write_text(json.dumps(profile,indent=2)+'\n')
report={'stage':'native_public_pr_source_resolution','source_sha256':profile['source_sha256'],'native_resolver_sha256':hashlib.sha256(Path(inspect.getfile(fetch_source)).read_bytes()).hexdigest(),'head':source['head'],'api_base_metadata':source['base'],'source_files':source['source_files'],'test_files':source['test_files'],'model_calls':0,'remote_workers':0,'note':'Native worker bootstraps pinned head and reverses source diff; API base metadata is not used as the tested baseline checkout.'}
(out/'resolution.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
