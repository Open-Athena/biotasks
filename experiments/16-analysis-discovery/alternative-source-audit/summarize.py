"""Reconcile fixed identities, separate document locators from weaker tutorial leads."""
import csv
import hashlib
import json
import urllib.parse
from collections import Counter
from pathlib import Path
ROOT=Path(__file__).resolve().parent
inputs=json.loads((ROOT/'inputs.json').read_text())
rows=[json.loads(l) for l in (ROOT/'final-observations.jsonl').read_text().splitlines()]
original=json.loads((ROOT.parent/'repo-notebook-audit/inventory.json').read_text())
expected={x['source_id']:x for x in original if not x['repo']}
assert len(rows)==len(inputs)==len(expected)==143
assert len({x['source_id'] for x in rows})==143
assert {x['source_id'] for x in rows}==set(expected)
adjudications=json.loads((ROOT/'adjudications.json').read_text())
for x in rows:
    rule=adjudications.get(x['name'],{})
    x['excluded_locators']=[n for n in x['documents'] if urllib.parse.urlparse(n['url']).hostname in rule.get('exclude_url_hosts',[])]
    x['documents']=[n for n in x['documents'] if n not in x['excluded_locators']]
    x['adjudication']=rule.get('reason')
    assert x['primary_domain']==expected[x['source_id']]['primary_domain']
    assert x['requests']
    x['document_locators']=[n for n in x['documents'] if n['format']!='Worked tutorial lead']
    x['tutorial_leads']=[n for n in x['documents'] if n['format']=='Worked tutorial lead']
    x['result']='document_located' if x['document_locators'] else ('tutorial_lead' if x['tutorial_leads'] else 'none_detected')
    x['formats']=sorted({n['format'] for n in x['document_locators']})
    x['request_errors']=sum('error' in r for r in x['requests'])

def counts(xs):
    return {'searched':len(xs),'document_located':sum(x['result']=='document_located' for x in xs),'tutorial_lead':sum(x['result']=='tutorial_lead' for x in xs),'none_detected':sum(x['result']=='none_detected' for x in xs),'with_limits':sum(x['has_access_or_budget_limit'] for x in xs)}
s={'all':counts(rows),'routes':{k:counts([x for x in rows if x['route']==k]) for k in dict.fromkeys(x['route'] for x in rows)},'domains':{k:counts([x for x in rows if x['primary_domain']==k]) for k in sorted({x['primary_domain'] for x in rows})},'rows':rows}
s['recovered_repository_links']=len({r for x in rows for r in x['recovered_repos']})
s['resolved_repository_trees']=len({t['repo'] for x in rows for t in x['trees'] if not t['repo'].startswith('http')})
s['formats']=dict(Counter(f for x in rows for f in x['formats']))
(ROOT/'summary.json').write_text(json.dumps(s,indent=2)+'\n')
with (ROOT/'source-results.csv').open('w') as f:
    w=csv.writer(f);w.writerow(['source_id','primary_domain','route','result','formats','request_errors','has_access_or_budget_limit'])
    for x in rows:w.writerow([x['source_id'],x['primary_domain'],x['route'],x['result'],'; '.join(x['formats']),x['request_errors'],x['has_access_or_budget_limit']])
validation={'fixed_identities':143,'searched':len(rows),'unchanged_domains':True,'identity_partition_1014':len(expected)+sum(bool(x['repo']) for x in original)==1014,'input_sha256':hashlib.sha256((ROOT/'inputs.json').read_bytes()).hexdigest(),'final_observations_sha256':hashlib.sha256((ROOT/'final-observations.jsonl').read_bytes()).hexdigest(),'result_counts':s['all']}
(ROOT/'validation.json').write_text(json.dumps(validation,indent=2)+'\n')
lines=['# Alternative-source discovery results','','All 143 previously unmapped source identities were searched. Original issue-5 labels are unchanged. This is a bounded locator search, not content screening or execution.','','| Route | Searched | Document locators | Tutorial leads only | No detection | Any access/budget limit |','| --- | ---: | ---: | ---: | ---: | ---: |']
for k,v in s['routes'].items():lines.append('| '+k+' | '+' | '.join(str(v[f]) for f in ['searched','document_located','tutorial_lead','none_detected','with_limits'])+' |')
lines += ['',f"Recovered {s['recovered_repository_links']} declared GitHub repository links; {s['resolved_repository_trees']} resolved to inspected trees. These are current metadata links, not replacements for the historical inventory mappings.",'','Counts are source identities, not unique notebooks, documents or repositories. Vignette HTML/PDF and R scripts are often paired representations. A located link is not evidence that its target was inspected or that its content is suitable. Tutorial leads use only HTML code-block/example markers and need manual screening.','', 'A source with an access/budget limit may still have usable evidence through another route. No detection is not absence. The previous 871-repository tree audit and this external-document pass have different detectors and time anchors; their positive counts should not be treated as one comparable notebook fraction.','','## Sources','']
for x in rows:
    lines.append(f"- **{x['name']}** ({x['primary_domain']}): {x['result']}; {len(x['document_locators'])} document representations, {len(x['tutorial_leads'])} tutorial leads; {len(x['requests'])} requests, {x['request_errors']} request errors.")
    for n in x['documents'][:3]:lines.append(f"  - [{n['format']}: {n['path']}]({n['url']})")
(ROOT/'results.md').write_text('\n'.join(lines)+'\n')
print(json.dumps({k:v for k,v in s.items() if k not in ('rows','domains')},indent=2))
