"""Check canonical grouping and unchanged source identities after recovery."""
import json
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT.parent))
from consolidate_documents import consolidate
raw={r['source_id']:r for r in json.loads((ROOT.parent/'alternative-source-audit/summary.json').read_text())['rows']}
rows=[json.loads(l) for l in (ROOT/'final-observations.jsonl').read_text().splitlines()]
for r in rows:
    original=raw[r['source_id']]['documents']
    groups=consolidate(original+r['documents'])
    for recovered in r['documents']:
        found=[g for g in groups if any(n.get('sha256')==recovered['sha256'] for n in g['representations'])]
        assert found and all(g['authoring_source_located'] for g in found)
        assert any(any(n['format']=='Rendered vignette' for n in g['representations']) for g in found)
        assert len(recovered['sha256'])==64 and recovered['bytes']>0
payload=json.loads((ROOT.parent/'inventory.html').read_text().split('window.BIOTASKS_DATA=',1)[1].split(';</script>',1)[0])
a=payload['source_inventory']
assert a['all']=={'sources':1014,'located':502,'lead':2,'none_detected':509,'unknown':1}
assert len({r['source_id'] for r in a['rows']})==1014
r=next(r for r in a['rows'] if r['name']=='alabaster.matrix')
assert len(r['documents'])==1 and r['documents'][0]['format']=='R Markdown'
print(json.dumps({'source_identities':1014,'source_totals_unchanged':True,'recovery_records_checked':len(rows),'canonical_grouping':'pass'}))
