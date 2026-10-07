"""Second pass: mirror pages for missing vignettes and linked tutorial pages.
Preserves original observations; appends supplemental evidence per identity.
"""
import json
import re
import resource
import urllib.parse as U
from scan import ROOT, archive, fetch, guard, hit, now, page

def main():
    started=now();guard(True);code=1
    inputs={x['source_id']:x for x in json.loads((ROOT/'inputs.json').read_text())}
    try:
        with (ROOT/'supplement.jsonl').open('w') as out:
            for line in (ROOT/'observations.jsonl').read_text().splitlines():
                rec=json.loads(line);old=len(rec['documents']);guard()
                if rec['route']=='Bioconductor package pages' and not old:
                    name={'go.db':'GO.db','org.hs.eg.db':'org.Hs.eg.db'}.get(rec['name'],rec['name'])
                    section='data/annotation' if name in ('GO.db','org.Hs.eg.db','GenomeInfoDbData') else 'bioc'
                    links=page(f'https://bioconductor.posit.co/packages/3.23/{section}/html/{name}.html',rec,True)
                    if not rec['documents']:
                        links+=page(f'https://bioconductor.posit.co/packages/3.22/{section}/html/{name}.html',rec,True)
                    if not rec['documents']:
                        archives=[u for u in links if '/src/contrib/' in u and u.endswith('.tar.gz')]
                        if archives:archive(archives[0],rec)
                elif not old:
                    # Follow the actual tutorial links emitted by project pages, excluding navigation-only assets.
                    leads=list(dict.fromkeys(x['url'] for x in rec['leads']))[:3]
                    for url in leads:
                        raw=fetch(url,rec)
                        if raw:
                            text=raw.decode(errors='replace')
                            if re.search(r'<(?:pre|code)[\s>]',text,re.I) and re.search(r'example|tutorial|walkthrough',text,re.I):
                                hit(rec,U.urlparse(url).path,'Worked tutorial lead',url,'HTML code blocks and tutorial/example text; needs biological-content review')
                    # A failed HTTP download may have an accessible HTTPS equivalent.
                    if not rec['documents'] and rec['source_url'].startswith('http:') and any(x.get('error') for x in rec['requests'] if x['url']==rec['source_url']):
                        archive('https:'+rec['source_url'][5:],rec)
                rec['status']='located' if rec['documents'] else 'no_detection_in_bounded_search'
                rec['has_access_or_budget_limit']=any('error' in x for x in rec['requests']) or any(not x['complete'] for x in rec['trees']+rec['archive_checks'])
                rec['finished_at']=now();out.write(json.dumps(rec)+'\n');out.flush()
                if len(rec['documents'])!=old:print(rec['name'],old,'->',len(rec['documents']),flush=True)
        code=0
    finally:
        run={'start':started,'end':now(),'exit_status':code,'pass':'recovery','estimate_mib':250,'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}
        with (ROOT/'runs.jsonl').open('a') as f:f.write(json.dumps(run)+'\n')
        print(json.dumps(run),flush=True)
if __name__=='__main__':main()
