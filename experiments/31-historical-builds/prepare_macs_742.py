"""Freeze deterministic second MACS case from original #28 evidence."""
import ast
import gzip
import hashlib
import json
from pathlib import Path
import re
import tarfile
ROOT=Path(__file__).resolve().parent
sha=lambda data:hashlib.sha256(data).hexdigest()
census=json.loads((ROOT.parents[3]/'experiments/28-catalogued-fields/history-wide/results/macs3-project__MACS-native-pytest-census.json').read_text())
selected=next(row for row in census['outcomes'] if row['original_status']=='failed' and row['original_reason']=='no fail-to-pass tests after validation' and row['stages']['pre']['removed_compiled_extensions'] and row['stages']['pre']['collection_error_marker'] and row['stages']['post']['collection_error_marker'])
assert selected['pr']==742 and selected['member']=='native-observations/batch-0003/validation-001-pr-742.json.gz'
archive=ROOT/'inputs-private/original-phase.tar.gz';assert sha(archive.read_bytes())==census['original_phase_sha256']
with tarfile.open(archive) as tar:
    names={m.name:m for m in tar if m.isfile()}
    base='native-observations/batch-0003/'
    records=[]
    for ordinal in ('0004','0005'):
        name=base+f'exec-{ordinal}-pr-742.json.gz';raw=tar.extractfile(names[name]).read();row=json.loads(gzip.decompress(raw));records.append((name,raw,row))
    discovery=json.loads(gzip.decompress(tar.extractfile(names[base+'discovery-pr-742.json.gz']).read()))
pre,post=[row['command'] for _,_,row in records]
pattern=r"git apply --verbose --reject - <<'EOF_R2E_VALIDATE'\n(.*?)\nEOF_R2E_VALIDATE"
prepatch=re.findall(pattern,pre,re.S);postpatch=re.findall(pattern,post,re.S)
assert len(prepatch)==1 and len(postpatch)==2 and prepatch[0]==postpatch[1]
source_patch,test_patch=postpatch
assert 'new file mode' not in source_patch and 'new file mode' not in test_patch
base_sha=re.search(r'git reset --hard ([0-9a-f]{40})',pre)[1]
assert re.search(r'git reset --hard ([0-9a-f]{40})',post)[1]==base_sha
cmds=re.search(r'echo R2E_START_TEST_OUTPUT\nset \+x\n\{\n(.*?)\n\} 2>&1',pre,re.S)[1]
assert cmds==re.search(r'echo R2E_START_TEST_OUTPUT\nset \+x\n\{\n(.*?)\n\} 2>&1',post,re.S)[1]
assert [cmds]==selected['original_test_cmds']
source_new_files=re.findall(r'^diff --git a/(.*?) b/.*?\nnew file mode',source_patch,re.M)
assert not source_new_files
rebuild=json.loads((ROOT/'inputs-private/macs-recorded-replay.json').read_text())['rebuild_cmds']
spec=__import__('importlib.util',fromlist=['spec_from_file_location'])
module_spec=spec.spec_from_file_location('rebuild_helper',ROOT/'candidate/pipelines/runtime_rebuild.py')
helper=spec.module_from_spec(module_spec);module_spec.loader.exec_module(helper)
def builder(path):
    tree=ast.parse(path.read_text());nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ('_heredoc_apply','_build_stage_script')]
    ns={'_HEREDOC':'EOF_R2E_VALIDATE','rebuild_script':helper.rebuild_script}
    exec(compile(ast.Module(body=nodes,type_ignores=[]),str(path),'exec'),ns);return ns['_build_stage_script']
original=builder(ROOT/'upstream/pipelines/pr_runtime_validate.py');candidate=builder(ROOT/'candidate/pipelines/pr_runtime_validate.py')
dest=ROOT/'inputs-private/macs-native-742';dest.mkdir(exist_ok=True,mode=0o700)
files={'source.patch':source_patch.encode(),'test.patch':test_patch.encode()};arms=[]
for name,build,kwargs in [('original',original,{}),('rebuild',candidate,{'rebuild_cmds':rebuild})]:
    stages={}
    for side,saved in [('pre',pre),('post',post)]:
        params={'apply_patch':source_patch if side=='post' else None,'apply_test_patch':test_patch,'test_cmds':[cmds]}
        script=build(base_sha,**params,**kwargs)
        if name=='original':assert script==saved and candidate(base_sha,**params,rebuild_cmds=None)==saved
        else:assert script.count(helper.rebuild_script(rebuild))==1
        data=script.encode();assert len(data)<128*1024
        files[name+'-'+side+'.sh']=data;stages[side]={'sha256':sha(data),'bytes':len(data)}
    arms.append({'name':name,'stages':stages})
for name,data in files.items():
    path=dest/name
    if path.exists():assert path.read_bytes()==data
    else:path.write_bytes(data);path.chmod(0o600)
image_source=json.loads((ROOT/'macs-longcheck-result-001.json').read_text())
manifest={'repo':'macs3-project/MACS','pr':742,'selection':'First completed native census row with removed compiled extensions and collection errors in both stages; static check confirms no new files in source/test patches',
          'base_sha':base_sha,'head_sha':discovery['headRefOid'],'original_archive_sha256':census['original_phase_sha256'],
          'original_stage_members':[{'path':n,'sha256':sha(raw)} for n,raw,_ in records],
          'commands':[cmds],'rebuild_cmds':rebuild,'arms':arms,'files':{n:{'sha256':sha(d),'bytes':len(d)} for n,d in files.items()},
          'default_off_original_stage_parity':True,'baseline_scripts_exactly_regenerated':True,'transport':'unchanged argv; all scripts below128KiB',
          'selection_limit':'Static compatibility screen only; native base-stage collection has not been retested after rebuild',
          'original_stage_pre_collection_errors':selected['stages']['pre']['parsed_statuses'].get('ERROR'),
          'original_stage_post_collection_errors':selected['stages']['post']['parsed_statuses'].get('ERROR'),
          'model_calls':0,'live_execution':False}
(ROOT/'macs-native-742-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(json.dumps({k:v for k,v in manifest.items() if k not in ('rebuild_cmds','arms','files','commands')}))
