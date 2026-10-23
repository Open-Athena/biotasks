"""Remove only the completed reconstruction's labeled images after archive readback."""
import hashlib,json,os,shutil,subprocess,tarfile,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parent
OWNER='biotasks29-ohif-reconstruct-001'
LABEL='org.open-athena.biotasks.owner='+OWNER
TOOLS=ROOT/'cleanup-tools'


def docker(*args,check=True):return subprocess.run([str(TOOLS/'docker'),*args],capture_output=True,text=True,timeout=60,check=check)


def main():
    report={'owner':OWNER,'removals':[],'model_calls':0}
    TOOLS.mkdir()
    try:
        pins=json.loads((ROOT/'docker-tool.json').read_text())
        with urllib.request.urlopen(pins['docker_url'],timeout=60) as src,(TOOLS/'docker.tgz').open('wb') as out:
            count=0
            while chunk:=src.read(1024*1024):
                count+=len(chunk);assert count<100*1024**2;out.write(chunk)
        assert hashlib.sha256((TOOLS/'docker.tgz').read_bytes()).hexdigest()==pins['docker_sha256']
        with tarfile.open(TOOLS/'docker.tgz') as t:(TOOLS/'docker').write_bytes(t.extractfile('docker/docker').read())
        (TOOLS/'docker').chmod(0o755)
        assert not docker('ps','-aq','--filter','label='+LABEL).stdout.strip(),'Unexpected running build resource; inspect instead'
        for attempt in range(16):
            ids=sorted(set(docker('image','ls','-aq','--no-trunc','--filter','label='+LABEL).stdout.split()))
            if not ids:break
            removed=False
            for ident in ids:
                inspected=docker('image','inspect',ident,check=False)
                if inspected.returncode:continue
                image=json.loads(inspected.stdout)[0]
                assert image['Config']['Labels']['org.open-athena.biotasks.owner']==OWNER
                result=docker('image','rm','-f',ident,check=False)
                report['removals'].append({'image':ident,'exit_code':result.returncode})
                removed|=result.returncode==0
            if not removed:break
        report['remaining_images']=docker('image','ls','-aq','--filter','label='+LABEL).stdout.split()
        report['remaining_containers']=docker('ps','-aq','--filter','label='+LABEL).stdout.split()
        report['verified_empty']=not report['remaining_images'] and not report['remaining_containers']
        assert report['verified_empty']
    finally:
        shutil.rmtree(TOOLS)
        report['tools_removed']=not TOOLS.exists()
        out=Path(os.environ['IRIS_OUTPUT_DIR']);out.mkdir(parents=True,exist_ok=True)
        (out/'cleanup-result.json').write_text(json.dumps(report,indent=2)+'\n')
        print('BIOTASKS29_CLEANUP='+json.dumps(report),flush=True)

if __name__=='__main__':main()
