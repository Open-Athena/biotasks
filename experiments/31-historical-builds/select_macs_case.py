"""Freeze earliest retained extension-removal pair without picking an easier case."""
import gzip,hashlib,json,re,subprocess,tarfile
from pathlib import Path
ROOT=Path(__file__).resolve().parent


def main():
    findings=json.loads((ROOT/'lifecycle-findings.json').read_text())
    source=ROOT/'inputs-private/original-phase.tar.gz'
    with source.open('rb') as f:assert hashlib.file_digest(f,'sha256').hexdigest()==findings['original_phase_sha256']
    selected=min(findings['pairs_with_extension_removal'],key=lambda row:row['member'])
    descriptor=selected['member'].rsplit('/',1)[0]+'/native-candidates.json'
    with tarfile.open(source,'r:gz') as archive:
        raw=archive.extractfile(selected['member']).read();assert hashlib.sha256(raw).hexdigest()==selected['sha256']
        outcome=json.loads(gzip.decompress(raw))
        descriptors=archive.extractfile(descriptor).read()
        number=int(re.search(r'-pr-(\d+)\.json\.gz$',selected['member'])[1])
        pr=next(row for row in json.loads(descriptors) if row['number']==number)
        rawboot=archive.extractfile(findings['source']['member']).read()
        assert hashlib.sha256(rawboot).hexdigest()==findings['source']['sha256']
        boot=json.loads(rawboot)
    checks=[]
    for number,line in enumerate(boot['dockerfile_reconstruction'].splitlines(),1):
        if line.startswith('RUN '):
            result=subprocess.run(['/bin/sh','-n','-c',line[4:]],capture_output=True,text=True,timeout=3)
            if result.returncode:checks.append({'line':number,'exit_code':result.returncode,'command_sha256':hashlib.sha256(line[4:].encode()).hexdigest(),'diagnostic':result.stderr.strip()})
    assert len(checks)==3
    result={'selection_rule':'Earliest retained batch/validation filename among original pairs with extension removal; no replacement case',
            'repo':'macs3-project/MACS','pr':pr['number'],'base_sha':pr['base_sha'],'head_sha':pr['head_sha'],'url':pr['url'],
            'descriptor_member':descriptor,'descriptor_member_sha256':hashlib.sha256(descriptors).hexdigest(),
            'validation':selected,'original_status':outcome['status'],'original_reason':outcome['reason'],
            'original_phase_sha256':findings['original_phase_sha256'],'reconstruction_sh_syntax_failures':checks,
            'baseline_status':'Saved recipe cannot execute unchanged: three RUN bodies fail default shell syntax checks',
            'live_comparison_run':False,'model_calls':0,
            'limits':['Syntax evidence is not a Docker build attempt','Deleted original image is unavailable; no replacement image or recipe repair applied','Native/package fixtures do not establish MACS task recovery']}
    (ROOT/'macs-case.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'pr':pr['number'],'base_sha':pr['base_sha'],'head_sha':pr['head_sha'],'shell_syntax_failures':len(checks)}))


if __name__=='__main__':main()
