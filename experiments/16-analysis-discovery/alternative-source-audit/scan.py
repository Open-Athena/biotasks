"""Bounded public discovery for all fixed issue-5 identities lacking GitHub mappings.
No installation or source execution. Findings are locators, not quality validation.
"""
import hashlib
import io
import json
import os
from pathlib import Path
import re
import resource
import subprocess
import tarfile
import time
import urllib.parse as U
import urllib.request as R
import zipfile
from datetime import datetime, timezone
from html.parser import HTMLParser

ROOT = Path(__file__).resolve().parent
EXT = {'.ipynb':'Jupyter', '.rmd':'R Markdown', '.rmarkdown':'R Markdown', '.qmd':'Quarto', '.rnw':'Sweave/knitr', '.rtex':'Sweave/knitr', '.nb':'Wolfram notebook', '.mlx':'MATLAB Live Script', '.livemd':'Livebook', '.dib':'.NET Interactive', '.rnb.html':'R notebook HTML export'}
def now(): return datetime.now(timezone.utc).isoformat()
def guard(start=False):
    mem = next(int(x.split()[1])*1024 for x in Path('/proc/meminfo').read_text().splitlines() if x.startswith('MemAvailable:'))
    load = os.getloadavg()[0]
    assert mem >= (2.5 if start else 2)*1024**3 and load < (1.5 if start else 2.5), (mem,load)
    if start: assert mem - 250*1024**2 >= 2*1024**3
    return {'available_bytes':mem,'load1':load}
def fmt(path): return next((v for k,v in EXT.items() if path.lower().endswith(k)), None)
class Links(HTMLParser):
    def __init__(self): super().__init__(); self.links=[]; self.current=None
    def handle_starttag(self, tag, attrs):
        if tag=='a': self.current=[dict(attrs).get('href',''),'']
    def handle_data(self, data):
        if self.current is not None: self.current[1]+=data
    def handle_endtag(self, tag):
        if tag=='a' and self.current is not None: self.links.append(self.current); self.current=None

def fetch(url, rec, cap=2*1024**2):
    guard(); e={'url':url}; rec['requests'].append(e)
    try:
        with R.urlopen(R.Request(url,headers={'User-Agent':'BioTasks-document-discovery/1.0'}),timeout=15) as response:
            raw=response.read(cap+1);e.update(final_url=response.url,status=response.status,bytes_read=len(raw),sha256=hashlib.sha256(raw).hexdigest())
        if len(raw)>cap: raise ValueError('response exceeds byte cap '+str(cap))
        return raw
    except Exception as error: e['error']=str(error)[:400]; return None

def hit(rec,path,kind,url,mechanism):
    if '.ipynb_checkpoints' in path: return
    item={'path':path,'format':kind,'url':url,'detection':mechanism}
    if not any(x['url']==url and x['path']==path for x in rec['documents']):rec['documents'].append(item)

def page(url,rec,bioc=False):
    raw=fetch(url,rec)
    if raw is None:return []
    parser=Links();parser.feed(raw.decode(errors='replace')); links=[]
    for href,label in parser.links:
        target=U.urljoin(url,href);path=U.urlparse(target).path;kind=fmt(path)
        if kind: hit(rec,path,kind,target,'linked filename; target content not inspected')
        elif '/vignettes/' in path and '/inst/doc/' in path and path.lower().endswith(('.html','.pdf','.r')):
            hit(rec,path,'Rendered vignette' if not path.lower().endswith('.r') else 'Vignette R script',target,'package vignette link; target content not inspected')
        elif not bioc and re.search(r'tutorial|worked example|walkthrough|notebook|vignette',label+' '+path,re.I):
            if target.startswith('http'):rec['leads'].append({'url':target,'label':label.strip()[:160]})
        links.append(target)
    return links

def archive(url,rec):
    raw=fetch(url,rec,16*1024**2)
    if raw is None:return
    total=0;count=0
    try:
        if raw[:2]==b'PK':
            z=zipfile.ZipFile(io.BytesIO(raw));entries=((x.filename,x.file_size,lambda x=x:z.open(x)) for x in z.infolist() if not x.is_dir())
        else:
            z=tarfile.open(fileobj=io.BytesIO(raw),mode='r|*');entries=((x.name,x.size,lambda x=x:z.extractfile(x)) for x in z if x.isfile())
        for name,size,opener in entries:
            total+=size;count+=1
            if total>64*1024**2 or count>20000:raise ValueError('archive expanded-size/member cap reached')
            kind=fmt(name)
            if kind:hit(rec,name,kind,url,'archive filename')
            elif re.search(r'(?:inst/doc|vignettes)/.*\.(html|pdf)$',name,re.I):hit(rec,name,'Rendered vignette',url,'archive vignette path; content not assessed')
            elif name.lower().endswith(('.py','.jl','.r','.md')) and size<=65536:
                f=opener(); text=f.read(65536).decode(errors='replace') if f else ''
                kind=None
                if ('import marimo' in text or 'from marimo' in text) and ('marimo.App(' in text or '@app.cell' in text):kind='marimo'
                elif '### A Pluto.jl notebook ###' in text:kind='Pluto'
                elif 'jupytext:' in text and ('text_representation:' in text or 'formats:' in text):kind='Jupytext'
                if kind:hit(rec,name,kind,url,'archive text signature')
        rec['archive_checks'].append({'url':url,'complete':True,'members':count,'expanded_bytes':total})
    except Exception as e:rec['archive_checks'].append({'url':url,'complete':False,'members':count,'expanded_bytes':total,'error':str(e)[:400]})

def github(url,rec):
    m=re.search(r'github.com/([^/\s]+/[^/#\s]+)',url)
    if not m:return
    repo=m[1].removesuffix('.git')
    if repo in rec['recovered_repos']:return
    rec['recovered_repos'].append(repo)
    def api(endpoint):
        guard();e={'url':'https://api.github.com/'+endpoint};rec['requests'].append(e)
        try:
            p=subprocess.run(['gh','api',endpoint],capture_output=True,timeout=20)
            e.update(bytes_read=len(p.stdout),sha256=hashlib.sha256(p.stdout).hexdigest())
            if p.returncode or len(p.stdout)>16*1024**2:raise ValueError(p.stderr.decode()[:300] or '16 MiB tree cap')
            return json.loads(p.stdout)
        except Exception as ex:e['error']=str(ex)[:400];return None
    c=api('repos/'+repo+'/commits/HEAD')
    if not c:return
    rev=c['sha'];t=api(f'repos/{repo}/git/trees/{rev}?recursive=1')
    if not t:return
    rec['trees'].append({'repo':repo,'revision':rev,'complete':not t.get('truncated',True),'entries':len(t.get('tree',[]))})
    for x in t.get('tree',[]):
        if x['type']=='blob' and fmt(x['path']):hit(rec,x['path'],fmt(x['path']),f'https://github.com/{repo}/blob/{rev}/'+x['path'],'recovered repository filename')

def alternative_git(url,rec):
    host=U.urlparse(url).hostname;path=U.urlparse(url).path.strip('/')
    if host=='gitlab.com':
        root='https://gitlab.com/api/v4/projects/'+U.quote(path,safe='')
        b=fetch(root+'/repository/commits?per_page=1',rec)
        if not b:return
        rev=json.loads(b)[0]['id']; count=0;complete=False
        for n in range(1,21):
            b=fetch(root+f'/repository/tree?recursive=true&per_page=100&page={n}&ref={rev}',rec)
            if not b:break
            xs=json.loads(b);count+=len(xs)
            for x in xs:
                if x['type']=='blob' and fmt(x['path']):hit(rec,x['path'],fmt(x['path']),url+'/-/blob/'+rev+'/'+x['path'],'GitLab tree filename')
            if len(xs)<100:complete=True;break
        rec['trees'].append({'repo':url,'revision':rev,'complete':complete,'entries':count})
    else:
        root='https://api.bitbucket.org/2.0/repositories/'+path
        b=fetch(root+'/commits?pagelen=1',rec)
        if not b:return
        rev=json.loads(b)['values'][0]['hash'];queue=[root+'/src/'+rev+'/?pagelen=100'];count=0;n=0
        while queue and n<60:
            b=fetch(queue.pop(0),rec);n+=1
            if not b:continue
            d=json.loads(b)
            if d.get('next'):queue.append(d['next'])
            for x in d.get('values',[]):
                count+=1
                if x['type']=='commit_directory':queue.append(root+'/src/'+rev+'/'+U.quote(x['path'])+'/?pagelen=100')
                elif fmt(x['path']):hit(rec,x['path'],fmt(x['path']),url+'/src/'+rev+'/'+x['path'],'Bitbucket tree filename')
        rec['trees'].append({'repo':url,'revision':rev,'complete':not queue and not any('error' in x for x in rec['requests']),'entries':count})

def scan(item):
    rec={'source_id':item['source_id'],'name':item['name'],'primary_domain':item['inventory']['primary_domain'],'started_at':now(),'source_url':item['source_url'],'requests':[],'documents':[],'leads':[],'trees':[],'archive_checks':[],'recovered_repos':[]}
    url=item['source_url'];host=U.urlparse(url).hostname or '';rec['route']='distribution'
    if item['source_id'].startswith('bioconductor:'):
        rec['route']='Bioconductor package pages'
        section='data/annotation' if item['name'].lower()=='genomeinfodbdata' else 'bioc'
        for base in ['https://bioconductor.org','https://bioconductor.posit.co']:
            links=page(base+'/packages/3.23/'+section+'/html/'+item['name']+'.html',rec,True)
            if links:break
    elif host in ('gitlab.com','bitbucket.org'):
        rec['route']=host;alternative_git(url,rec)
        page(url,rec)
    else:
        metadata=[]
        for evidence in item['evidence_urls'][:2]:
            if 'raw.githubusercontent.com' in evidence:
                b=fetch(evidence,rec)
                if b:
                    t=b.decode(errors='replace');metadata += re.findall(r'^\s*(?:home|doc_url|dev_url):\s*[\"\']?(https?://[^\s\"\']+)',t,re.M)
            elif 'pypi.org/pypi/' in evidence:
                b=fetch(evidence,rec)
                if b:
                    info=json.loads(b)['info'];metadata += [x for x in (info.get('project_urls') or {}).values() if x]
        if 'cpan.' in host:
            dist=U.unquote(url.rsplit('/',1)[-1]);dist=re.sub(r'-v?\d.*','',dist)
            b=fetch('https://fastapi.metacpan.org/v1/release/'+dist,rec)
            if b:
                res=json.loads(b).get('resources',{});metadata += [res.get('homepage','')]
                repository=res.get('repository',{});metadata += [repository.get('web','') if isinstance(repository,dict) else repository]
        rec['metadata_links']=list(dict.fromkeys(metadata))
        for link in rec['metadata_links'][:4]:
            if 'github.com/' in link:github(link,rec)
            elif link.startswith('http'):page(link,rec)
        archive(url,rec)
        if not rec['metadata_links']:
            page(U.urljoin(url,'/'),rec)
    rec['status']='located' if rec['documents'] else 'no_detection_in_bounded_search'
    rec['has_access_or_budget_limit']=any('error' in x for x in rec['requests']) or any(not x['complete'] for x in rec['trees']+rec['archive_checks'])
    rec['finished_at']=now();return rec

def main():
    start=now();initial=guard(True);status=1;done=0
    out=ROOT/'observations.jsonl';seen={json.loads(l)['source_id'] for l in out.read_text().splitlines()} if out.exists() else set()
    try:
        with out.open('a') as f:
            for item in json.loads((ROOT/'inputs.json').read_text()):
                if item['source_id'] in seen:continue
                guard()
                rec=scan(item);f.write(json.dumps(rec)+'\n');f.flush();done+=1
                print(json.dumps({'new':done,'name':rec['name'],'status':rec['status'],'documents':len(rec['documents'])}),flush=True)
        status=0
    finally:
        log={'start':start,'end':now(),'exit_status':status,'newly_searched':done,'estimate_mib':250,'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'initial_resources':initial}
        with (ROOT/'runs.jsonl').open('a') as f:f.write(json.dumps(log)+'\n')
        print(json.dumps(log),flush=True)
if __name__=='__main__':main()
