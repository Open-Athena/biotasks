import collections,csv,hashlib,importlib.util,json,math,re
from pathlib import Path
base=Path('docs/experiments/bio-task-generation/01-discovery');root=Path('/tmp/bio-discovery-20260929');scratch=root/'top200';folder=base/'data/top200-2026-09-29'
for p,expected in json.loads((scratch/'baseline-hashes.json').read_text()).items():assert hashlib.sha256(Path(p).read_bytes()).hexdigest()==expected,p
assert hashlib.sha256((base/'inventory.json').read_bytes()).hexdigest()=='e2cda0e700c76e37f28e619462cdbf5d2c7a81609af0c389fea49064fbe91c65'
rows=list(csv.DictReader((folder/'rankings-2026-09-29.csv').open()));ann={r['source_id']:r for r in csv.DictReader((folder/'source-annotations-2026-09-29.csv').open())}
sources={r['source_id']:r for r in json.loads((folder/'source-observations-2026-09-29.json').read_text())}
with (root/'bioconda-packages.tsv').open() as f:bc={r['package']:int(r['total']) for r in csv.DictReader(f,delimiter='\t')}
with (root/'bioconductor-scores.tsv').open() as f:bi={r['Package']:int(r['Download_score']) for r in csv.DictReader(f,delimiter='\t')}
py={r['project']:int(r['downloads_30d']) for r in json.loads((root/'top100/pypi-counts-without-mirrors.json').read_text())['data']}
gh={r['metadata']['nameWithOwner']:r['metadata']['stargazerCount'] for r in json.loads((root/'top100/github-source-metadata.json').read_text())['records'] if r['metadata']}
raw={'bioconda':bc,'bioconductor':bi,'pypi':py,'github':gh}
for row in rows:assert int(row['score'])==max(raw[row['ranking']][p] for p in row['packages'].split(';')),row
ranks={name:[r for r in rows if r['ranking']==name] for name in raw};d=json.loads((folder/'expansion-results-2026-09-29.json').read_text())
assert len(rows)==800 and len(ann)==len(sources)==672
for name,rs in ranks.items():
 assert len(rs)==len({r['source_id'] for r in rs})==200
 for start,stop,key in [(0,100,'first100'),(100,200,'second100'),(0,200,'full200')]:
  subset=[ann[r['source_id']] for r in rs[start:stop]];counts=collections.Counter(x['primary_domain'] for x in subset);expected=d['rankings'][name][key]
  assert dict(sorted(counts.items()))==expected['domains'];assert len({x['manual_topic'] for x in subset})==expected['manual_topic_bins']
  assert math.isclose(math.exp(-sum(n/len(subset)*math.log(n/len(subset)) for n in counts.values())),expected['effective_domain_bins'])
 for block in d['rankings'][name]['blocks']:
  previous={ann[r['source_id']]['manual_topic'] for r in rs[:block['start_rank']-1]};current={ann[r['source_id']]['manual_topic'] for r in rs[block['start_rank']-1:block['end_rank']]}
  assert sorted(current-previous)==block['new_topics']
for pair in d['pairs']:
 for depth,v in pair['by_depth'].items():
  a={r['source_id'] for r in ranks[pair['first']][:int(depth)]};b={r['source_id'] for r in ranks[pair['second']][:int(depth)]}
  assert len(a&b)==v['shared'] and math.isclose(len(a&b)/len(a|b),v['jaccard'])
# Verify the rendered catalog independently of its generation loop.
lines=[l for l in (base/'ranking-additions.md').read_text().splitlines() if re.match(r'\| \d+ \|',l)];assert len(lines)==400
for i,(name,rs) in enumerate(ranks.items()):
 for line,row in zip(lines[i*100:(i+1)*100],rs[100:],strict=True):
  source=sources[row['source_id']];assert f"| {row['rank']} |" in line and source['source_url'] in line and f"{int(row['score']):,}" in line
for path in [base/'ranking-expansion.md',base/'ranking-additions.md']:
 for url in re.findall(r'\]\(([^)]+)\)',path.read_text()):
  if '://' not in url and not url.startswith('#'):assert (path.parent/url.split('#')[0]).exists(),url
for row in sources.values():assert row['source_url'].startswith(('https://','http://'))
print('PASS: 800 scores match cached provider responses; unchanged 95/top100 files; 672 unique annotated sources; independent entropy/overlap/block checks; 400 catalog entries; local links.')
