"""Reconcile fixed inventory, scan observations and original labels offline."""
import csv
import io
import json
from collections import Counter
from pathlib import Path
ROOT=Path(__file__).resolve().parent

def main():
    inventory=json.loads((ROOT/'inventory.json').read_text())
    observations=[json.loads(l) for l in (ROOT/'observations.jsonl').read_text().splitlines()]
    assert len({x['source_id'] for x in observations})==len(observations)
    by_id={x['source_id']:x for x in observations};rows=[]
    for item in inventory:
        o=by_id.get(item['source_id'])
        if o:
            assert (item['repo'],item['revision'])==(o['repo'],o['revision'])
            assert o['status'] in {'present','absent','unknown'}
            assert o['status']!='absent' or not o['truncated']
            assert (o['status']=='present')==bool(o['notebooks'])
        rows.append({**item,'status':o['status'] if o else ('not_scanned' if item['repo'] else 'unmapped'),'notebook_count':len(o['notebooks']) if o else None,'count_complete':o.get('notebook_count_complete',False) if o else False,'examples':o['notebooks'][:5] if o else [],'error':o.get('error') if o else None,'truncated':o.get('truncated') if o else None})
    assert len(rows)==1014 and sum(bool(r['repo']) for r in rows)==871
    assert set(by_id)<={r['source_id'] for r in rows}
    def stats(rs):
        c=Counter(r['status'] for r in rs);mapped=sum(bool(r['repo']) for r in rs);known=c['present']+c['absent']
        return {'sources':len(rs),'mapped':mapped,**{k:c[k] for k in ['present','absent','unknown','not_scanned','unmapped']},'present_fraction_resolved':c['present']/known if known else None,'present_lower_bound_mapped':c['present']/mapped if mapped else None}
    domains={d:stats([r for r in rows if r['primary_domain']==d]) for d in sorted({r['primary_domain'] for r in rows})}
    routes={d:stats([r for r in rows if d in r['rankings']]) for d in ['bioconda','bioconductor','pypi','github']}
    result={'input_commit':'4d1efa0593f40be515b0428fa30be783a54407e9','definition':'At least one .ipynb blob path at the previously recorded repository revision; .ipynb_checkpoints excluded. No notebook content validation or execution.','all':stats(rows),'domains':domains,'routes':routes,'notebook_paths_found':sum(r['notebook_count'] or 0 for r in rows),'rows':rows}
    (ROOT/'summary.json').write_text(json.dumps(result,indent=2)+'\n')
    output=io.StringIO();w=csv.DictWriter(output,fieldnames=['primary_domain',*next(iter(domains.values())).keys()]);w.writeheader()
    for d,v in domains.items():w.writerow({'primary_domain':d,**v})
    (ROOT/'domain-coverage.csv').write_text(output.getvalue())
    print(json.dumps({k:v for k,v in result.items() if k not in ['rows','domains']}))
if __name__=='__main__':main()
