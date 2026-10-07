"""Reconcile recovery attempts without changing original discovery evidence."""
import json
from collections import Counter
from pathlib import Path
ROOT=Path(__file__).resolve().parent
rows={}
for filename in ['observations.jsonl','followup.jsonl','archive-followup.jsonl','refinement.jsonl']:
    if not (ROOT/filename).exists():continue
    for line in (ROOT/filename).read_text().splitlines():
        x=json.loads(line);sid=x['source_id']
        if sid not in rows:rows[sid]=x;continue
        r=rows[sid];r['requests']+=x['requests'];r['documents']+=x['documents'];r['unresolved']=x['unresolved'];r['end']=x['end'];r.setdefault('notes',[]).extend(x.get('notes',[]))
        if x.get('archive'):r.setdefault('archive_followups',[]).append(x['archive'])
original=json.loads((ROOT.parent/'alternative-source-audit/summary.json').read_text())['rows']
expected={r['source_id']:[n for n in r['documents'] if n['format']=='Rendered vignette'] for r in original if any(n['format']=='Rendered vignette' for n in r['documents'])}
assert set(rows)==set(expected)
for sid,r in rows.items():
    for n in r['documents']:
        if 'group_path' not in n:
            matches=[v for v in expected[sid] if v['url']==n['group_url']]
            assert len(matches)==1
            n['group_path']=matches[0]['path']
    def key(n):return (n.get('group_url',n['url']),n.get('group_path',n['path']))
    assert len({key(n) for n in r['documents']})==len(r['documents'])
    assert {key(n) for n in r['documents']}|{key(n) for n in r['unresolved']}=={key(n) for n in expected[sid]}
    assert not {key(n) for n in r['documents']}&{key(n) for n in r['unresolved']}
s={'sources_checked':len(rows),'rendered_locators':sum(len(v) for v in expected.values()),'recovered_documents':sum(len(r['documents']) for r in rows.values()),'unresolved_documents':sum(len(r['unresolved']) for r in rows.values()),'sources_with_recovery':sum(bool(r['documents']) for r in rows.values()),'formats':dict(Counter(n['format'] for r in rows.values() for n in r['documents'])),'unresolved':[{'source_id':r['source_id'],'documents':r['unresolved']} for r in rows.values() if r['unresolved']]}
assert s['rendered_locators']==s['recovered_documents']+s['unresolved_documents']
(ROOT/'summary.json').write_text(json.dumps(s,indent=2)+'\n')
(ROOT/'final-observations.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in rows.values()))
print(json.dumps(s,indent=2))
