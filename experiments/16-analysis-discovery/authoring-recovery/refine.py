"""Resolve inspected lowercase/prose-only Sweave sources; identify PDF stubs."""
import json,hashlib,resource,io,tarfile
from recover import ROOT,fetch,guard,now
start=now();guard(True);records=[]
rows={r['source_id']:r for r in map(json.loads,(ROOT/'final-observations.jsonl').read_text().splitlines())}
for sid in ['bioconductor:globalancova','bioconductor:snpstats','bioconductor:edger','bioconductor:limma']:
    prior=rows[sid];r={'source_id':sid,'requests':[],'documents':[],'unresolved':[],'notes':[],'end':now()}
    for n in prior['unresolved']:
        ext='.rnw' if 'globalancova' in sid else '.Rnw'
        u=n['url'].replace('https://bioconductor.org','https://bioconductor.statistik.tu-dortmund.de').rsplit('.',1)[0]+ext
        b=fetch(u,r);t=b.decode(errors='replace') if b else ''
        if '\\includepdf' in t and len(t)<1000:
            r['unresolved'].append(n);r['notes'].append({'rendered_url':n['url'],'reason':'Rnw is a short PDF inclusion wrapper, not the guide authoring content.','wrapper_url':u});continue
        assert b and '\\VignetteIndexEntry' in t and ('\\section' in t or '<<' in t)
        r['documents'].append({'url':u,'path':u.split('/inst/doc/')[-1],'format':'Sweave/knitr','group_url':n['url'],'group_path':n['path'],'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b),'detection':'Authoring text inspected; lowercase Sweave or substantive prose-only Sweave, not PDF wrapper'})
    records.append(r)
(ROOT/'refinement.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in records))
with (ROOT/'runs.jsonl').open('a') as f:f.write(json.dumps({'pass':'source refinements','start':start,'end':now(),'exit_status':0,'estimate_mib':150,'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss})+'\n')
print([(r['source_id'],len(r['documents']),len(r['unresolved'])) for r in records])
