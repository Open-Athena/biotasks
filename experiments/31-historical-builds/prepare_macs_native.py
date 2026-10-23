"""Freeze original MACS PR792 stage inputs and the single rebuild intervention."""
import ast
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import tarfile
ROOT=Path(__file__).resolve().parent
sha=lambda data:hashlib.sha256(data).hexdigest()
case=json.loads((ROOT/'macs-case.json').read_text())
archive=ROOT/'inputs-private/original-phase.tar.gz';assert sha(archive.read_bytes())==case['original_phase_sha256']
with tarfile.open(archive) as tar:
    members={m.name:m for m in tar if m.isfile()}
    records=[]
    for name in sorted(n for n in members if 'batch-0001/exec-' in n and '-pr-792.json.gz' in n):
        raw=tar.extractfile(members[name]).read();v=json.loads(gzip.decompress(raw))
        if 'echo R2E_START_TEST_OUTPUT' in v['command']:records.append((name,raw,v))
assert len(records)==2
pre,post=[v['command'] for _,_,v in records]
pattern=r"git apply --verbose --reject - <<'EOF_R2E_VALIDATE'\n(.*?)\nEOF_R2E_VALIDATE"
prepatch=re.findall(pattern,pre,re.S);postpatch=re.findall(pattern,post,re.S)
assert len(prepatch)==1 and len(postpatch)==2 and prepatch[0]==postpatch[1]
source_patch,test_patch=postpatch
cmds=re.search(r'echo R2E_START_TEST_OUTPUT\nset \+x\n\{\n(.*?)\n\} 2>&1',pre,re.S)[1]
assert cmds==re.search(r'echo R2E_START_TEST_OUTPUT\nset \+x\n\{\n(.*?)\n\} 2>&1',post,re.S)[1]
payload=json.loads((ROOT/'inputs-private/macs-recorded-replay.json').read_text())
rebuild=payload['rebuild_cmds'];assert rebuild
spec=importlib.util.spec_from_file_location('rebuild_helper',ROOT/'candidate/pipelines/runtime_rebuild.py')
helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
def load(path):
    tree=ast.parse(path.read_text());nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ('_heredoc_apply','_build_stage_script')]
    ns={'_HEREDOC':'EOF_R2E_VALIDATE','rebuild_script':helper.rebuild_script}
    exec(compile(ast.Module(body=nodes,type_ignores=[]),str(path),'exec'),ns);return ns['_build_stage_script']
original=load(ROOT/'upstream/pipelines/pr_runtime_validate.py');candidate=load(ROOT/'candidate/pipelines/pr_runtime_validate.py')
dest=ROOT/'inputs-private/macs-native-792';dest.mkdir(exist_ok=True,mode=0o700)
files={'source.patch':source_patch.encode(),'test.patch':test_patch.encode()};arms=[]
for arm,builder,kwargs in [('original',original,{}),('rebuild',candidate,{'rebuild_cmds':rebuild})]:
    stages={}
    for side,saved in [('pre',pre),('post',post)]:
        params={'apply_patch':source_patch if side=='post' else None,'apply_test_patch':test_patch,'test_cmds':[cmds]}
        script=builder(case['base_sha'],**params,**kwargs)
        if arm=='original':
            assert script==saved
            assert candidate(case['base_sha'],**params,rebuild_cmds=None)==saved
        else:
            expected=helper.rebuild_script(rebuild)
            assert script.count(expected)==1
            assert script.index(expected)<script.index('echo R2E_START_TEST_OUTPUT')
        data=script.encode();files[arm+'-'+side+'.sh']=data
        stages[side]={'sha256':sha(data),'bytes':len(data)}
    arms.append({'name':arm,'stages':stages})
assert max(len(v) for k,v in files.items() if k.endswith('.sh'))<128*1024
for name,data in files.items():
    target=dest/name
    if target.exists():assert target.read_bytes()==data
    else:target.write_bytes(data);target.chmod(0o600)
image=json.loads((ROOT/'macs-longcheck-result-001.json').read_text())
result={'repo':case['repo'],'pr':792,'base_sha':case['base_sha'],'head_sha':case['head_sha'],'original_archive_sha256':case['original_phase_sha256'],
        'original_stage_members':[{'path':n,'sha256':sha(raw)} for n,raw,_ in records],
        'commands':[cmds],'rebuild_cmds':rebuild,'arms':arms,'files':{n:{'sha256':sha(d),'bytes':len(d)} for n,d in files.items()},
        'default_off_original_stage_parity':True,'baseline_scripts_exactly_regenerated':True,'transport':'unchanged argv; all scripts below128KiB',
        'image_id':image['retained_image_id'],'image_tag':image['retained_image_tag'],'image_owner':image['run_id'],
        'live_execution':False,'model_calls':0,'limits':['No dependency/test command repair','Rebuild syntax/version constraints preserved literally','No native outcomes or exported controls yet']}
(ROOT/'macs-native-manifest.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result))
