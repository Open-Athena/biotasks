import csv,hashlib,json,math,re,subprocess,sys
from collections import Counter
from itertools import combinations
from pathlib import Path
root=Path.cwd();scratch=Path('/tmp/bio-discovery-20260929');out=scratch/'top100';base=root/'docs/experiments/bio-task-generation/01-discovery';data=base/'data'
assert hashlib.sha256((base/'inventory.json').read_bytes()).hexdigest()=='e2cda0e700c76e37f28e619462cdbf5d2c7a81609af0c389fea49064fbe91c65'

def csv_rows(path,delimiter=','):
 with path.open() as f:return list(csv.DictReader(f,delimiter=delimiter))
rankings=csv_rows(data/'rankings-2026-09-29.csv');labels={r['source_id']:r for r in csv_rows(data/'source-annotations-2026-09-29.csv')};observations={r['source_id']:r for r in json.loads((data/'source-observations-2026-09-29.json').read_text())}
raw={
 'bioconda':{r['package']:int(r['total']) for r in csv_rows(scratch/'bioconda-packages.tsv','\t')},
 'bioconductor':{r['Package']:int(r['Download_score']) for r in csv_rows(scratch/'bioconductor-scores.tsv','\t')},
 'pypi':{r['project']:int(r['downloads_30d']) for r in json.loads((out/'pypi-counts-without-mirrors.json').read_text())['data']},
 'github':{r['metadata']['nameWithOwner']:r['metadata']['stargazerCount'] for r in json.loads((out/'github-source-metadata.json').read_text())['records'] if r['metadata']},
}
for row in rankings:
 assert int(row['score'])==max(raw[row['ranking']][name] for name in row['packages'].split(';')),row
 for evidence in labels[row['source_id']]['evidence_urls'].split(';'):assert evidence.startswith(('http://','https://')),evidence
results_path=data/'ranking-results-2026-09-29.json';results=json.loads(results_path.read_text());before=hashlib.sha256(results_path.read_bytes()).hexdigest()
subprocess.run(['uv','run','--no-project','experiments/bio_tasks/01_discovery/analyze_rankings.py','--data-dir',str(data),'--date','2026-09-29'],check=True)
assert before==hashlib.sha256(results_path.read_bytes()).hexdigest(),'Analysis output not deterministic'
sets={route:{r['source_id'] for r in rankings if r['ranking']==route} for route in raw}
assert len(set.union(*sets.values()))==335
for pair in results['pairs']:
 a,b=sets[pair['first']],sets[pair['second']];assert pair['intersection']==len(a&b);assert pair['jaccard']==len(a&b)/len(a|b)
for route,ids in sets.items():
 c=Counter(labels[k]['primary_domain'] for k in ids);types=Counter(labels[k]['source_type'] for k in ids);r=results['rankings'][route]
 assert dict(c)==r['domains'];assert dict(types)==r['source_types'];assert sum(c.values())==100
 effective=math.prod((100/n)**(n/100) for n in c.values());assert math.isclose(effective,r['effective_domain_bins'])
report=(base/'ranking-comparison.md').read_text();catalog=(base/'ranking-lists.md').read_text();assert len(re.findall(r'^\| \d+ \|',catalog,re.M))==400
for page in [base/'ranking-comparison.md',base/'ranking-lists.md',base/'index.md',base/'adoption.md']:
 for link in re.findall(r'\]\(([^)]+)\)',page.read_text()):
  if link.startswith(('http://','https://','#')):continue
  assert (page.parent/link.split('#')[0]).exists(),(page,link)
assert "unexpected keyword argument 'ignore_init_summary'" in (scratch/'mkdocs-baseline.log').read_text()
print('Verified all 400 scores against raw provider responses, 335 annotations, overlap/diversity, 400 catalog entries, local links, deterministic regeneration and unchanged original95 inventory.')
