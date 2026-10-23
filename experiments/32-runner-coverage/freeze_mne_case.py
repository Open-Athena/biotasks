"""Freeze earliest retained MNE validation pair with exact original stage scripts."""
import ast
import gzip
import hashlib
import json
from pathlib import Path
import re
import tarfile
from check_deleted_targets import load
from pytest_target_policy import select

ROOT=Path(__file__).resolve().parent
sha=lambda b:hashlib.sha256(b).hexdigest()
readback=json.loads((ROOT/'mne-input-readback.json').read_text())
path=ROOT/readback['local_path'];assert sha(path.read_bytes())==readback['archive_sha256']
with tarfile.open(path) as tar:
    members={m.name:m for m in tar if m.isfile()}
    def raw(name):return tar.extractfile(members[name]).read()
    def zipped(name):return json.loads(gzip.decompress(raw(name)))
    validations=sorted(n for n in members if '/validation-' in n)
    first=validations[0];assert first.endswith('validation-001-pr-14445.json.gz')
    outcome=zipped(first)
    discovery='native-observations/batch-0000/discovery-pr-14445.json.gz'
    metadata=zipped(discovery)
    commands=[]
    for name in sorted(n for n in members if '/exec-' in n and '-pr-14445.json.gz' in n):
        record=zipped(name)
        if 'echo R2E_START_TEST_OUTPUT' in record['command']:
            commands.append((name,record))
    assert len(commands)==2
    pre,post=[r['command'] for _,r in commands]
    pattern=r"git apply --verbose --reject - <<'EOF_R2E_VALIDATE'\n(.*?)\nEOF_R2E_VALIDATE"
    prepatches=re.findall(pattern,pre,re.S);postpatches=re.findall(pattern,post,re.S)
    assert len(prepatches)==1 and len(postpatches)==2 and prepatches[0]==postpatches[1]
    patch,testpatch=postpatches
    base=re.search(r'^git reset --hard ([a-f0-9]{40})$',pre,re.M)[1]
    assert base==re.search(r'^git reset --hard ([a-f0-9]{40})$',post,re.M)[1]
    bootname=next(n for n in members if n.startswith('bootstrap/') and n.endswith('/bootstrap.json'))
    boot=json.loads(raw(bootname));transname=bootname.replace('/bootstrap.json','/transcript.jsonl')
    transcript=[json.loads(line) for line in raw(transname).splitlines()]
    actions=[]
    for turn in transcript:
        assert turn['action']=='BASH'
        code=int(re.match(r'^exit=(\d+)\n',turn['observation'])[1])
        actions.append({'step':turn['step'],'command':turn['input'],'command_sha256':sha(turn['input'].encode()),'expected_exit_code':code,'original_observation_sha256':sha(turn['observation'].encode()),'timeout_seconds':300})
    assert len(actions)==12 and all(a['expected_exit_code']==127 for a in actions)
    payload={'repo':boot['repo'],'ref':boot['ref'],'base_image':re.search(r'^FROM (.+)$',boot['dockerfile_reconstruction'],re.M)[1],
        'actions':actions,'test_cmds':boot['test_cmds'],'rebuild_cmds':boot['rebuild_cmds'],'original_smoke_passed':boot['smoke_passed'],'original_verify_passed':boot['verify_passed']}
    tree=ast.parse((ROOT/'upstream/pipelines/pr_runtime_validate.py').read_text())
    nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ('_heredoc_apply','_build_stage_script')]
    ns={'_HEREDOC':'EOF_R2E_VALIDATE'};exec(compile(ast.Module(body=nodes,type_ignores=[]),'pinned_stages','exec'),ns)
    for script,source in [(pre,None),(post,patch)]:
        assert script==ns['_build_stage_script'](base,apply_patch=source,apply_test_patch=testpatch,test_cmds=boot['test_cmds'])
    # Bind changed destinations via the enabled integration's deletion-aware helper.
    funcs=load(ROOT/'candidate-policy/pipelines/pr_runtime.py')
    paths=funcs['_runnable_test_files_in_patch'](testpatch)
    decisions=[select(cmd,paths,enabled=True) for cmd in boot['test_cmds']]
    assert all(d['status']=='selected' for d in decisions)
    dest=ROOT/'inputs-private/mne-case-14445';dest.mkdir(mode=0o700,exist_ok=True)
    files={'source.patch':patch.encode(),'test.patch':testpatch.encode(),'pre.sh':pre.encode(),'post.sh':post.encode(),'replay.json':(json.dumps(payload,indent=2)+'\n').encode()}
    for name,data in files.items():
        target=dest/name
        if target.exists():assert target.read_bytes()==data
        else:target.write_bytes(data);target.chmod(0o600)
    result={'repo':boot['repo'],'pr':14445,'selection':'Earliest original retained validation ordinal; no result-based reselection',
        'base':base,'head':metadata['headRefOid'],'bootstrap_ref':boot['ref'],'original_archive_sha256':readback['archive_sha256'],
        'validation_member':first,'discovery_member':discovery,'test_paths':paths,'original_commands':boot['test_cmds'],'candidate_decisions':decisions,
        'original_stage_scripts_exactly_regenerated':True,'files':{n:{'bytes':len(d),'sha256':sha(d)} for n,d in files.items()},
        'original_stages':[{'member':n,'exit_code':r['result']['exit_code'],'duration_sec':r['result']['duration_sec'],'command_sha256':sha(r['command'].encode())} for n,r in commands],
        'bootstrap':{'actions':len(actions),'all_recorded_exits':127,'assistant_tail_actions':sum(bool(re.search(r'^Assistant:',a['command'],re.M)) for a in actions),
            'smoke_passed':boot['smoke_passed'],'verify_passed':boot['verify_passed'],'transcript_sha256':sha(raw(transname))},
        'original_validation_status':outcome['status'],'original_f2p':outcome['fail_to_pass'],'original_p2p':outcome['pass_to_pass'],
        'model_calls':0,'remote_jobs':0,'limits':['No command repaired or executed','Original stages timed out; no regrading','Recorded exit parity cannot prove dependency/image equivalence','Faithful executable environment required before live targeting comparison']}
(ROOT/'mne-frozen-case.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result))
