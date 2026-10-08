"""Apply explicit pilot not-applicable judgments to the saved classification pass."""
import json
from collections import Counter
from pathlib import Path
ROOT=Path(__file__).resolve().parent
pilot={r['id']:r for r in json.loads((ROOT.parent/'annotations.json').read_text())}
docs=[]
for line in (ROOT/'annotations.jsonl').open():
 r=json.loads(line)
 if r.get('pilot_id') in pilot:
  states=pilot[r['pilot_id']].get('facet_review',{});r['reviewed_facet_states']=states
  for facet,state in states.items():
   if state=='not_applicable':r['facet_states'][facet]=state
 docs.append(r)
(ROOT/'annotations.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in docs))
p=ROOT/'classification-summary.json';summary=json.loads(p.read_text());summary['facet_coverage']={f:dict(Counter(r['facet_states'][f] for r in docs if r['counted'])) for f in ['scientific_field','modality','operation']};p.write_text(json.dumps(summary,indent=2)+'\n')
print('Reconciled explicit pilot facet states; label assignments unchanged.')
