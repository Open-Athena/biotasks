"""Pin recovered www.github.com links and inspect their additional host README."""
import datetime,hashlib,json,resource
from pathlib import Path
from acquire import ROOT,get,guard
from classify import rows
def main():
 guard(True);rev='f6dc65546c3a9aed53f26f0cbd3ad518a2c48504';out=[]
 for r in rows(ROOT/'recovery.jsonl'):
  if r['url'].startswith('https://www.github.com/eyurtsev/kor/') and r['status']=='confirmed':
   path=r['url'].split('/blob/main/',1)[1];url=f'https://raw.githubusercontent.com/eyurtsev/kor/{rev}/{path}';raw,_=get(url)
   assert hashlib.sha256(raw).hexdigest()==r['sha256']
   out.append({'document_key':r['document_key'],'original_url':r['url'],'pinned_url':f'https://github.com/eyurtsev/kor/blob/{rev}/{path}','revision':rev,'sha256':r['sha256'],'match':'exact_original_bytes'})
 (ROOT/'external-github-pins.json').write_text(json.dumps(out,indent=2)+'\n')
 url=f'https://raw.githubusercontent.com/eyurtsev/kor/{rev}/README.md';raw,route=get(url,128*1024);filename='repo-'+hashlib.sha256(b'eyurtsev/kor').hexdigest()+'.json'
 (ROOT/'content'/filename).write_text(json.dumps({'repository':'eyurtsev/kor','text':raw.decode()}))
 record={'repository':'eyurtsev/kor','revision':rev,'revisions':[rev],'url':url,'sha256':hashlib.sha256(raw).hexdigest(),'route':route,'status':'acquired','content_file':filename,'observed_at':datetime.datetime.now(datetime.timezone.utc).isoformat()}
 if not any(r['repository']=='eyurtsev/kor' for r in rows(ROOT/'repository-acquisition.jsonl')):
  with (ROOT/'repository-acquisition.jsonl').open('a') as h:h.write(json.dumps(record)+'\n')
 print('Pinned',len(out),'source versions and inspected additional README.')
if __name__=='__main__':main()
