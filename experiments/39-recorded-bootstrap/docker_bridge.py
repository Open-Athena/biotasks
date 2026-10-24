#!/usr/bin/env python3
"""Generic bounded Docker/Compose transport; original tasks stay byte-identical."""
import json
import os
from pathlib import Path
import subprocess
import sys
import time

from common import content_sha


def tagged_recipe(raw,owner):
    lines=raw.splitlines(keepends=True)
    positions=[i for i,line in enumerate(lines) if line.upper().startswith(b'FROM ')]
    assert len(positions)==1
    lines.insert(positions[0]+1,('LABEL biotasks.run='+owner+'\n').encode())
    return b''.join(lines)


def append(path,row):
    with Path(path).open('a') as handle:handle.write(json.dumps(row)+'\n')


def dependency_binding(real,owner):
    descriptor=json.loads(Path('/work/bootstrap-dependency.json').read_text())
    report=json.loads(Path('/work/evidence/bootstrap-replay.json').read_text())
    assert report['run_id']==owner and report['stage']=='dependency_verified'
    assert report['descriptor_sha256']==content_sha(Path('/work/bootstrap-dependency.json').read_bytes())
    assert report['actions_sha256']==descriptor['actions_sha256'] and report['source_commit']==descriptor['bootstrap_ref']
    assert report['base_image_id']==descriptor['expected_base_image_id']
    assert report['smoke_passed'] and report['verify_passed'] and report['source_sandbox_removed_before_fresh_check']
    assert report['bootstrap_containers_removed'] and report['context_removed'] and report['docker_config_removed']
    current=json.loads(subprocess.check_output([real,'image','inspect',descriptor['dependency_ref']]))[0]
    assert current['Id']==report['image_id'] and current['Config']['Labels']['biotasks.run']==owner
    return descriptor['dependency_ref'],report['image_id']


def image_ancestry(real,image_id,expected):
    chain=[];seen=set();current=image_id
    for _ in range(128):
        assert current and current not in seen, 'Cannot prove exact reconstructed dependency ancestry'
        chain.append(current);seen.add(current)
        if current==expected:return chain
        row=json.loads(subprocess.check_output([real,'image','inspect',current]))[0]
        assert row['Id']==current
        current=row.get('Parent')
    raise AssertionError('Unbounded image ancestry')


def build_image(real,owner,context,raw,kind,task=None):
    assert kind=='task', 'Dependency was already initialized by the original action procedure'
    dependency_ref,dependency_id=dependency_binding(real,owner)
    assert [line for line in raw.splitlines() if line.startswith(b'FROM ')]==[('FROM '+dependency_ref).encode()]
    digest=content_sha(raw)
    tag=owner+'-'+('bootstrap' if kind=='bootstrap' else task.lower())+':'+digest[:12]
    found=subprocess.run([real,'image','inspect',tag],capture_output=True,text=True)
    started=time.time()
    row=dict(kind=kind,task=task,image=tag,dockerfile_sha256=digest,started=started)
    row['bootstrap_dependency_image_id']=dependency_id
    history=Path('/work/evidence/bounded-builds.jsonl')
    if kind=='task' and history.exists():
        previous=[json.loads(line) for line in history.read_text().splitlines()]
        failed=[r for r in previous if r['kind']=='task' and r['dockerfile_sha256']==digest and r['exit_code']!=0]
        if failed:
            row.update(exit_code=failed[0]['exit_code'],finished=time.time(),
                blocked_by_prior_build_failure=True,source_failure_started=failed[0]['started'])
            append(history,row)
            return row
    if found.returncode==0:
        image=json.loads(found.stdout)[0];assert image['Config']['Labels']['biotasks.run']==owner
        row.update(cached=True,exit_code=0,image_id=image['Id'],finished=time.time())
    else:
        assert 'No such image' in found.stderr, 'Do not mistake daemon errors for image absence'
        effective=tagged_recipe(raw,owner)
        recipe=Path('/work/infra')/(digest+'.Dockerfile');recipe.write_bytes(effective)
        command=[real,'build','--force-rm','--cpu-period=100000','--cpu-quota=150000',
            '--memory=6g','--memory-swap=6g','--network=iris-egress',
            '--label','biotasks.run='+owner,'--tag',tag,'-f',str(recipe),str(context)]
        append('/work/evidence/build-starts.jsonl',row)
        result=subprocess.run(command,env=dict(os.environ,DOCKER_BUILDKIT='0'),check=False)
        row.update(exit_code=result.returncode,finished=time.time(),ownership_label_only=True,
            effective_dockerfile_sha256=content_sha(effective),cpu_limit=1.5,memory_bytes=6*1024**3)
        if result.returncode==0:row['image_id']=json.loads(subprocess.check_output([real,'image','inspect',tag]))[0]['Id']
    if row['exit_code']==0:
        row['dependency_ancestry']=image_ancestry(real,row['image_id'],dependency_id)
        row['dependency_ancestry_verified']=True
    append('/work/evidence/bounded-builds.jsonl',row)
    return row


def capture_identity(real,owner,image,task,digest,family):
    inspected=json.loads(subprocess.check_output([real,'image','inspect',image]))[0]
    assert inspected['Config']['Labels']['biotasks.run']==owner
    image_id=inspected['Id']
    _,dependency_id=dependency_binding(real,owner)
    ancestry=image_ancestry(real,image_id,dependency_id)
    exports=family['effective_test_path_exports']
    assert len(exports)==2 and all(line.startswith('export PATH=') and '\n' not in line for line in exports)
    entry='\n'.join(exports)+'\nexec python3 -c \"$1\"'
    script='''import json,sys,platform,subprocess,shutil
tools={}
for name in ('python3','node','npm','pnpm'):
    path=shutil.which(name);row={'path':path}
    if path and name!='pnpm':
        result=subprocess.run([path,'--version'],capture_output=True,text=True,timeout=15)
        row.update(exit_code=result.returncode,stdout=result.stdout.strip(),stderr=result.stderr.strip())
    tools[name]=row
packages=subprocess.run([sys.executable,'-m','pip','--disable-pip-version-check','freeze'],capture_output=True,text=True,timeout=30)
import hashlib,os
locks={}
for name in ('pnpm-lock.yaml','package.json','node_modules/.pnpm/lock.yaml','node_modules/.modules.yaml'):
    path='/workspace/'+name
    if os.path.isfile(path):
        assert os.path.getsize(path)<16*1024**2
        with open(path,'rb') as source:locks[name]={'bytes':os.path.getsize(path),'sha256':hashlib.file_digest(source,'sha256').hexdigest()}
print(json.dumps(dict(git_head=subprocess.check_output(['git','-C','/workspace','rev-parse','HEAD'],text=True).strip(),python=sys.version,platform=platform.platform(),tools=tools,python_packages=packages.stdout.splitlines() if packages.returncode==0 else None,lock_files=locks,effective_path=os.environ['PATH'])))
'''
    result=subprocess.run([real,'run','--rm','--name',owner+'-identity',
        '--cpus=1','--memory=256m','--memory-swap=256m','--network=none',
        '--label','biotasks.run='+owner,'--entrypoint','/bin/bash',image_id,'-c',entry,'--',script],
        capture_output=True,text=True,timeout=90,check=True)
    record=json.loads(result.stdout)
    record.update(task=task['task'],image=image,image_id=image_id,dockerfile_sha256=digest,captured=time.time())
    record.update(bootstrap_dependency_image_id=dependency_id,dependency_ancestry=ancestry,dependency_ancestry_verified=True,
        test_commands_sha256=family['test_commands_sha256'],effective_test_path_exports=exports)
    append('/work/evidence/image-identities.jsonl',record)
    assert record['git_head']==task['base_commit']
    return image_id


def main():
    real=os.environ['BIOTASKS_REAL_DOCKER'];owner=os.environ['BIOTASKS_RUN_ID']
    family=json.loads(Path('/work/family.json').read_text());assert family['run_id']==owner
    args=sys.argv[1:]
    assert not args or args[0]!='prefix-build', 'Recorded dependency initialization replaces native clean-prefix build'
    if not args or args[0]!='compose':
        assert not any(v in {'run','create','build'} for v in args[:2]), 'Use bounded execution path'
        os.execv(real,[real,*args])
    if args[1:]==['version']:os.execv(real,[real,*args])
    context=Path(os.environ['CONTEXT_DIR']).resolve()
    assert context.is_relative_to(Path('/work/outputs')) and context.name=='environment'
    task=next(t for t in family['tasks'] if t['task']==context.parent.name)
    raw=(context/'Dockerfile').read_bytes();digest=content_sha(raw)
    spec=next(f for f in task['files'] if f['path'].endswith('/environment/Dockerfile'))
    assert digest==spec['sha256']
    image=owner+'-'+task['task'].lower()+':'+digest[:12]
    commands={'build','up','down','ps','exec','cp','logs','config','stop','rm'}
    index=1
    while index<len(args) and args[index] not in commands:
        assert args[index] in {'--project-name','--project-directory','-f'};index+=2
    assert index<len(args);command=args[index]
    if command=='build':
        assert args[index:]==['build'];return build_image(real,owner,context,raw,'task',task['task'])['exit_code']
    if command=='up':image=capture_identity(real,owner,image,task,digest,family)
    infra=Path('/work/infra');infra.mkdir(exist_ok=True)
    overlay=infra/(digest+'.json')
    overlay.write_text(json.dumps(dict(services=dict(main=dict(image=image,build=None,pull_policy='never',
        cpus=1.0,mem_limit='6g',memswap_limit='6g',network_mode='iris-egress',labels={'biotasks.run':owner}))))+'\n')
    routed=args[:index]+['-f',str(overlay)]+args[index:]
    if command=='up':routed+=['--no-build','--pull','never']
    os.execv(real,[real,*routed])


if __name__=='__main__':raise SystemExit(main())
