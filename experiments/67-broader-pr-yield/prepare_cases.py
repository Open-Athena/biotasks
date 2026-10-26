"""Build data-only history inputs; no models, execution or public raw upload."""
import hashlib,json,shutil
from pathlib import Path
from biotasks.generation import resources
from biotasks.validation.files import inventory,json_sha,sha
root=Path(__file__).resolve().parent
old=root.parents[2]/'66/experiments/66-fresh-nibabel'
base=json.loads((old/'manifest.json').read_text())
counts=json.loads((root/'history-counts.json').read_text())
known={'scverse/anndata':{2652,2634},'nipy/nibabel':{1574},'jeetsukumaran/DendroPy':{259},'biopython/biopython':set()}
manifest={**base,'id':'issue67','archive':{'kind':'local'}}
manifest['client_profile']=json.loads((root/'client-profile.json').read_text())
def ref(p):return {'path':str(p),'sha256':sha(p)}
manifest['price_quote']=ref(root/'price-quote.json');manifest['cases']=[]
summary=[]
for row in counts['repositories']:
 repo=row['repo']; slug=repo.split('/')[1].lower(); case=root/'cases'/slug;case.mkdir(exist_ok=True)
 source=root/'inputs-private/inventory'/repo.replace('/','__')/'inventory.jsonl'
 rows=[json.loads(x) for x in source.read_text().splitlines()]
 rows.sort(key=lambda x:(x['createdAt'],x['number']),reverse=True)
 excluded=[r['number'] for r in rows if r['number'] in known[repo]]
 rows=[r for r in rows if r['number'] not in known[repo]]
 native=json.loads((old/'native-config.json').read_text());native['repo'].update(url='https://github.com/'+repo,ref=row['bootstrap_ref']);native['pipeline']['options'].update(limit=100,since='1970-01-01',until='2026-10-17');native['output']['dataset_name']='biotasks67-'+slug
 (case/'native-config.json').write_text(json.dumps(native,indent=2)+'\n')
 candidates={'upstream_revision':base['repo2rlenv_revision'],'kind':'history-identities-v1','repo':repo,**native['pipeline']['options'],'cutoff_utc':'2026-10-17T23:59:59+00:00','source_inventory_sha256':sha(source),'candidates':[{'number':r['number'],'head_sha':r['headRefOid'],'state':'MERGED'} for r in rows]}
 resources.history_policy().validate(candidates)
 (case/'candidates.json').write_text(json.dumps(candidates,indent=2)+'\n')
 notices=case/'notices';notices.mkdir(exist_ok=True)
 (notices/'scope.json').write_text(json.dumps({'repo':repo,'bootstrap_ref':row['bootstrap_ref'],'public_raw_eligibility':'Not established for whole historical cohort. Preserve locally; publish only reviewed summaries until source/data notices are reviewed.','metadata_license':row['license']},indent=2)+'\n')
 manifest['cases'].append({'id':slug,'run_id':'biotasks67-'+slug+'-001','mode':'fresh','native_config':ref(case/'native-config.json'),'candidates':ref(case/'candidates.json'),'notices':{'path':str(notices),'inventory_sha256':json_sha(inventory(notices))},'publication':{'eligible':False,'review':'Historical raw evidence retained privately under HOME pending content and notices review; no blanket public redistribution. Eligible aggregate results will be archived separately.'},'targeting_policy':'workspace-python-v1'})
 summary.append({'repo':repo,'inventory':len(rows)+len(excluded),'excluded_known_exports':excluded,'pending':len(rows),'batch_size':100,'repository_cap':None})
(root/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
(root/'dedup-preflight.json').write_text(json.dumps({'prior_known_source':'Issue27 AnnData2652/2634 and issues62/66; cutoff excludes later known exports. No known task is regenerated.','repositories':summary},indent=2)+'\n')
print(json.dumps(summary,indent=2))
