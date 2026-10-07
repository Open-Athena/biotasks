"""Follow declared documentation for all 37 non-Bioconductor identities."""
import json
import re
import resource
import urllib.parse as U
from scan import ROOT, fetch, github, guard, hit, now, page

def main():
    guard(True);start=now();code=1
    inputs={x['source_id']:x for x in json.loads((ROOT/'inputs.json').read_text())}
    try:
        with (ROOT/'final-observations.jsonl').open('w') as out:
            for line in (ROOT/'supplement.jsonl').read_text().splitlines():
                rec=json.loads(line);guard();old=len(rec['documents'])
                if rec['route']!='Bioconductor package pages':
                    links=[]
                    for url in inputs[rec['source_id']]['evidence_urls']:
                        if 'pypi.org/pypi/' in url:
                            raw=fetch(url,rec)
                            if raw:
                                info=json.loads(raw)['info'];links += [info.get('home_page') or '']
                                links += re.findall(r'https?://[^\s<>\)\"]+',info.get('description') or '')[:12]
                        elif 'raw.githubusercontent.com' in url:
                            raw=fetch(url,rec)
                            if raw:links+=re.findall(r'^\s*(?:home|doc_url|dev_url):\s*[\"\']?(https?://[^\s\"\']+)',raw.decode(errors='replace'),re.M)
                    visited={x['url'] for x in rec['requests']}
                    # Revisit project pages to obtain documentation links, but do not retry rate-limited hosts.
                    limited={U.urlparse(x['url']).hostname for x in rec['requests'] if '429' in x.get('error','')}
                    for url in list(dict.fromkeys(links))[:6]:
                        if not url.startswith('http') or U.urlparse(url).hostname in limited:continue
                        if 'github.com/' in url:github(url,rec)
                        else:
                            found=page(url,rec)
                            for child in list(dict.fromkeys(u for u in found if re.search(r'tutorial|notebook|userguide|manual|/docs?/',u,re.I)))[:3]:
                                if child not in visited and U.urlparse(child).hostname not in limited:
                                    page(child,rec);visited.add(child)
                    # Inspect evidence for leads, without claiming scientific suitability.
                    for url in list(dict.fromkeys(x['url'] for x in rec['leads']))[:6]:
                        if U.urlparse(url).hostname in limited:continue
                        raw=fetch(url,rec)
                        if raw:
                            text=raw.decode(errors='replace')
                            if re.search(r'<(?:pre|code)[\s>]',text,re.I) and re.search(r'example|tutorial|walkthrough',text,re.I):
                                hit(rec,U.urlparse(url).path,'Worked tutorial lead',url,'HTML code blocks and example text; needs biological-content review')
                rec['has_access_or_budget_limit']=any('error' in x for x in rec['requests']) or any(not x['complete'] for x in rec['trees']+rec['archive_checks'])
                rec['finished_at']=now();rec['status']='located' if rec['documents'] else 'no_detection_in_bounded_search'
                out.write(json.dumps(rec)+'\n');out.flush()
                if rec['route']!='Bioconductor package pages':print(rec['name'],old,'->',len(rec['documents']),flush=True)
        code=0
    finally:
        log={'start':start,'end':now(),'pass':'declared documentation','exit_status':code,'estimate_mib':250,'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}
        with (ROOT/'runs.jsonl').open('a') as f:f.write(json.dumps(log)+'\n')
        print(json.dumps(log),flush=True)
if __name__=='__main__':main()
