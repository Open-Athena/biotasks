"""Bounded read-only gh acquisition for the predeclared sample."""
import datetime
import hashlib
import json
from pathlib import Path
import selectors
import subprocess
import time

ROOT = Path(__file__).resolve().parent
CAP = 2 * 1024 * 1024


def fetch(args):
    process = subprocess.Popen(['gh', 'api', *args], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    sel = selectors.DefaultSelector()
    sel.register(process.stdout, selectors.EVENT_READ, 'out')
    sel.register(process.stderr, selectors.EVENT_READ, 'err')
    buffers = {'out': bytearray(), 'err': bytearray()}
    deadline = time.monotonic() + 45
    try:
        while sel.get_map():
            if time.monotonic() > deadline:
                raise TimeoutError('45-second API deadline')
            for key, _ in sel.select(0.5):
                chunk = key.fileobj.read1(65536)
                if not chunk:
                    sel.unregister(key.fileobj)
                    continue
                buffers[key.data].extend(chunk)
                if sum(map(len, buffers.values())) > CAP:
                    raise ValueError('2 MiB response cap')
        rc = process.wait(timeout=2)
        if rc:
            raise RuntimeError(f'gh exited {rc}: {buffers["err"].decode(errors="replace")[:400]}')
        return bytes(buffers['out'])
    finally:
        if process.poll() is None:
            process.kill()
            process.wait(timeout=5)
        sel.close()
        process.stdout.close()
        process.stderr.close()


def main():
    private=ROOT/'inputs-private'
    private.mkdir(mode=0o700,exist_ok=True)
    rows=[]
    for case in json.loads((ROOT/'live-cases.json').read_text())['cases']:
        ident=case['identity'];number=ident['number'];base=ident['base_sha'];head=ident['head_sha']
        record={'pr':number,'base_sha':base,'head_sha':head,'retrieved_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
        queries=[('metadata',[f'repos/matchms/matchms/pulls/{number}','--jq','{number,state,merged,base_sha:.base.sha,head_sha:.head.sha}']),
                 ('diff',[f'repos/matchms/matchms/compare/{base}...{head}','-H','Accept: application/vnd.github.diff'])]
        for kind,args in queries:
            target=private/f'{number}.{kind}'
            try:
                if target.exists():data=target.read_bytes()
                else:
                    data=fetch(args);target.write_bytes(data);target.chmod(0o600)
                record[kind]={'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest(),'path':str(target.relative_to(ROOT))}
                if kind=='metadata':record['current_metadata']=json.loads(data)
            except Exception as error:record[kind]={'unavailable':type(error).__name__+': '+str(error)}
        rows.append(record)
        (ROOT/'live-case-acquisition.json').write_text(json.dumps({'scope':'Pinned-ref GitHub compare diffs; raw patches private; not original unretained script bytes','rows':rows},indent=2)+'\n')
        print(number,{k:record[k].get('bytes',record[k].get('unavailable')) for k in ['metadata','diff']})

if __name__=='__main__':main()
