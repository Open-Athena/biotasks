"""Validate evidence links and pilot boundary invariants without executing source code."""
import hashlib
import json
from pathlib import Path

root = Path(__file__).resolve().parent
rows = json.loads((root/'annotations.json').read_text())
vocab = json.loads((root/'vocabulary.json').read_text())
repos = json.loads((root/'repository-annotations.json').read_text())
sources = {}
for name in ['source-content.json','extension-source-content.json']:
    sources.update({r['id']:r for r in json.loads((root/name).read_text())})
assert len(rows)==len(sources)==14
assert len({r['hosting_repository'] for r in rows})==len(repos)==12
assert sum(r['status']=='unreviewed' for r in repos)==4
role_counts = {}
for r in rows:
    src=sources[r['id']]
    assert src['sha256']==r['source_sha256']
    assert src['revision']==r['revision'] and len(r['revision'])==40
    locators={c['locator'] for c in src['chunks']}
    assert not r['executed'] and not r['independent_review']
    seen=set()
    for a in r['labels']:
        assert a['term'] in vocab[a['facet']]
        assert set(a['evidence']) <= locators and a['evidence']
        key=(a['facet'],a['term'],a.get('role'),a.get('target'))
        assert key not in seen
        seen.add(key)
        if a['facet']=='operation':
            assert a['role'] in vocab['operation_roles'] and a['target']
            role_counts.setdefault(a['term'],{}).setdefault(a['role'],set()).add(r['id'])
# Source-backed checks address real false-coverage cases discovered during inspection.
def source(id,loc):
    return next(c['text'] for c in sources[id]['chunks'] if c['locator']==loc)
def roles(id,term):
    r=next(r for r in rows if r['id']==id)
    return {a['role'] for a in r['labels'] if a['facet']=='operation' and a['term']==term}
assert 'define_clonotype_clusters' in source('L25','cell:52')
assert 'provided data' in source('L25','cell:13')
assert roles('L25','clustering')=={'implemented','upstream_supplied'}
assert roles('L25','dimension-reduction')=={'implemented','upstream_supplied'}
assert 'runSingleTraitGwas' in source('E05','line:613')
assert roles('E05','association')=={'exercise'}
assert 'preprocessQuantile' in source('L40','line:221')
assert roles('L40','normalization')=={'discussed_only'}
assert 'get_blob_to_path' in source('G04','cell:6')
assert roles('G04','data-access')=={'implemented'}
assert 'pcv.analyze.size' in source('L01','cell:28')
assert 'rgb-image' in {a['term'] for r in rows if r['id']=='L01' for a in r['labels']}
assert 'microscopy' not in {a['term'] for r in rows if r['id']=='L01' for a in r['labels']}
assert not roles('L17','clustering')
counts={f:{term:len({r['id'] for r in rows if any(a['facet']==f and a['term']==term for a in r['labels'])}) for term in vocab[f]} for f in ['scientific_field','modality']}
result={'passed':True,'scope':'Identity, source-locator, deduplicated counts and source-backed boundary checks; not independent biological validation', 'documents':14,'hosting_repositories':12,'readmes_reviewed':8,'repository_fields_supported':4,'repository_fields_insufficient':4,'repository_unreviewed':4,'counts':counts,'operation_counts_by_role':{term:{role:len(ids) for role,ids in byrole.items()} for term,byrole in role_counts.items()},'fingerprints':{name:hashlib.sha256((root/name).read_bytes()).hexdigest() for name in ['sample.json','extension-sample.json','annotations.json','repository-annotations.json','vocabulary.json']}}
(root/'validation.json').write_text(json.dumps(result,indent=2)+'\n')
print('PASS: 14 documents, 12 hosts, 8 separately inspected READMEs; source-backed boundary and distinct-count checks.')
