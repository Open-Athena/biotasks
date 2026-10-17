"""Prepare one accepted parent for native SETA Evol/DataArc loaders; no models."""
import hashlib
import json
import shutil
import tomllib
from pathlib import Path

import tomli_w
from repo2rlenv.emitter.bundle import inspect_bundle
from repo2rlenv.pipelines.recipes.seta_evol.recipe import load_parents
from repo2rlenv.pipelines.recipes.dataarc.recipe import load_seeds, _CANARIES
from repo2rlenv.spec.recipe_options import TaskEvolutionOptions, DataArcOptions


def prepare(root):
    acceptance = json.loads((root/'evidence/pr2633-acceptance/acceptance.json').read_text())
    assert acceptance['status']=='accepted_for_bounded_pilot'
    source=root/'evidence/marin-pr2633-preparation/harbor-task'
    for name,digest in acceptance['asset_sha256'].items():
        assert hashlib.sha256((source/name).read_bytes()).hexdigest()==digest
    out=root/'seeds/pr2633-parent-v1';out.mkdir(parents=True,exist_ok=False)
    parent=out/'parent';shutil.copytree(source,parent)
    original=tomllib.loads((source/'task.toml').read_text())
    config=tomllib.loads((parent/'task.toml').read_text())
    identity=inspect_bundle(parent)['bundle_hash']
    config['metadata']['repo2env']['bundle_hash']=identity
    (parent/'task.toml').write_text(tomli_w.dumps(config))
    assert inspect_bundle(parent)['integrity_passed']
    config['metadata']['repo2env'].pop('bundle_hash')
    assert config==original
    for name in acceptance['asset_sha256']:
        if name!='task.toml':assert (parent/name).read_bytes()==(source/name).read_bytes()
    # Eligibility remains based on original material, before DataArc filtering.
    matched=[]
    for f in parent.rglob('*'):
        if f.is_file():
            for needle in _CANARIES:
                if needle in f.read_text().lower():matched.append({'path':str(f.relative_to(parent)),'marker':needle})
    assert not matched, 'Original exclusion marker requires review before loading'
    evo=TaskEvolutionOptions(target=3,max_candidates=10,variants_per_parent=3)
    arc=DataArcOptions(target=3,max_candidates=10)
    generated={'seta_evol':load_parents(parent,evo),'dataarc':load_seeds(parent,arc)}
    report={'stage':'native_parent_loader_preparation_only','cohort':'pr2633-parent-v1',
            'accepted_parent_tasks':1,'parent_task_id':acceptance['task_id'],
            'parent_bundle_hash':identity,'parent_transform':'Only native bundle_hash metadata added; all executable configuration and other file bytes unchanged.',
            'related_variant_policy':'All children retain the same parent lineage and must share any train/evaluation split; variants are not independent source problems.',
            'biological_competency':'Numerical software repair with limited biological reasoning; upstream regression fixture, not an observed assay.',
            'original_exclusion_marker_matches':matched,'recipes':{},'model_calls':0,'built_children':0,'accepted_children':0}
    for name,records in generated.items():
        report['recipes'][name]={'options':(evo if name=='seta_evol' else arc).model_dump(mode='json'),
            'input_pool_size':len(records),'attempt_ceiling':10,
            'records':[{'title':x['title'],'sha256':hashlib.sha256(json.dumps(x,sort_keys=True).encode()).hexdigest()} for x in records]}
    arc_files=generated['dataarc'][0]['seed_files']
    report['dataarc_context_limits']={'reference_patch_omitted':'solution/patch.diff' not in arc_files,
        'verifier_module_omitted':'tests/verifier.py' not in arc_files,
        'f2p_p2p_lists_omitted':all('tests/'+x not in arc_files for x in ('f2p.json','p2p.json')),
        'test_script_source_characters':len((parent/'tests/test.sh').read_text()),
        'test_script_retained_characters':len(arc_files['tests/test.sh']),
        'truncated_seed_files':[name for name in arc_files if len('\n'.join((parent/name).read_text().splitlines()))>3500],
        'interpretation':'Native loader loses referenced oracle/grader assets and truncates seed-file excerpts over 3500 characters; this parent test script is below that limit. Preserve this limitation in any baseline run; a fuller context would be a separate intervention.'}
    (out/'manifest.json').write_text(json.dumps(report,indent=2)+'\n')
    return report


if __name__=='__main__':
    result=prepare(Path(__file__).resolve().parent)
    print(json.dumps({'parent_bundle_hash':result['parent_bundle_hash'],'pools':{k:v['input_pool_size'] for k,v in result['recipes'].items()},'context_limits':result['dataarc_context_limits'],'model_calls':0}))
