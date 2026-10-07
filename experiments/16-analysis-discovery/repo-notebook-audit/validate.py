"""Independent accounting checks against preserved issue-5 inputs and observations."""
import csv
import hashlib
import json
from collections import Counter
from pathlib import Path
ROOT=Path(__file__).resolve().parent
provenance=json.loads((ROOT/'input-provenance.json').read_text())
for path,digest in provenance['sha256'].items():assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==digest
original=json.loads((ROOT/'source-observations.json').read_text())
labels={r['source_id']:r for r in csv.DictReader((ROOT/'source-annotations.csv').open())}
rankings=list(csv.DictReader((ROOT/'rankings.csv').open()))
observations=[json.loads(l) for l in (ROOT/'observations.jsonl').read_text().splitlines()]
report=json.loads((ROOT/'summary.json').read_text());rs=report['rows'];obs={r['source_id']:r for r in observations}
assert len(obs)==len(observations)==871
assert len(rs)==1014 and {r['source_id'] for r in rs}=={r['source_id'] for r in original}
original_by_id={r['source_id']:r for r in original}
for r in rs:
    g=original_by_id[r['source_id']].get('github')
    assert r['repo']==(g['name'] if g else None)
    assert r['revision']==(g['head'] if g else None)
    assert r['primary_domain']==labels[r['source_id']]['primary_domain']
    assert r['rankings']=={x['ranking']:int(x['rank']) for x in rankings if x['source_id']==r['source_id']}
    o=obs.get(r['source_id'])
    if o:
        assert r['notebook_count']==len(o['notebooks'])
        assert r['formats']==sorted({n['format'] for n in o['notebooks']})
        assert all('.ipynb_checkpoints' not in n['path'].split('/') for n in o['notebooks'])
        assert r['status']!='none_detected' or (not o['truncated'] and not o['notebooks'])
        for probe in o.get('signature_probes',[]):assert probe.get('prefix_bytes',0)<=65536
    else:assert r['status']=='unmapped'
for grouping,key in [('domains','primary_domain'),('routes','rankings')]:
    for name,total in report[grouping].items():
        subset=[r for r in rs if (name in r[key] if grouping=='routes' else r[key]==name)]
        assert total['sources']==len(subset)
        c=Counter(r['status'] for r in subset)
        for status in ['present','none_detected','unknown','not_scanned','unmapped']:assert total[status]==c[status]
        assert total['mapped']==len(subset)-c['unmapped']
        assert total['formats']==dict(Counter(f for r in subset for f in r['formats']))
assert sum(v['sources'] for v in report['domains'].values())==1014
assert all(v['sources']==300 for v in report['routes'].values())
assert report['all']['not_scanned']==0
result={'passed':True,'checks':['input SHA256 matches issue-5 copies','1014 unique source identities','871 unique repository observations','unchanged primary labels and ranking memberships','all domain and route status/format cells independently recounted','checkpoint exclusion and 64KiB prefix cap','no unscanned mapped repository'],'notebook_execution':False}
(ROOT/'validation.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
