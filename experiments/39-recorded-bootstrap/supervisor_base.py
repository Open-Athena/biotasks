"""One generic no-model family job; no repository-specific execution branches."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import tarfile
import time
import urllib.request

from common import sha,unpack_task_archive


class Supervisor:
    ALLOWED_MODES=('native_inline',)
    def __init__(self,root,out,config):
        self.root=Path(root);self.out=Path(out);self.config=config;self.run=config['run_id']
        self.tools=self.root/'tools';self.controller=self.run+'-controller';self.volume=self.run+'-work'
        self.created=False
        self.report=dict(run_id=self.run,repo=config['repo'],started=time.time(),model_calls=0,task_repairs=0,new_capacity=False)
        self.report['tasks']=[dict(task=t['task'],state='unstarted') for t in config['tasks']]

    def checkpoint(self):
        (self.out/'work-state.json').write_text(json.dumps(self.report,indent=2)+'\n')

    def docker(self,*args,timeout=90,check=True):
        return subprocess.run([str(self.tools/'docker'),*args],capture_output=True,text=True,timeout=timeout,check=check)

    def fetch(self,url,path,expected,maximum=100*1024**2):
        with urllib.request.urlopen(url,timeout=60) as source,Path(path).open('wb') as dest:
            total=0
            while chunk:=source.read(1024*1024):
                total+=len(chunk);assert total<=maximum;dest.write(chunk)
        assert sha(path)==expected

    def exec_logged(self,name,args,seconds):
        with (self.out/name).open('w') as log:
            return subprocess.run([str(self.tools/'docker'),'exec',*args],stdout=log,stderr=subprocess.STDOUT,timeout=seconds,check=False)

    def validate(self):
        assert self.config['mode'] in self.ALLOWED_MODES
        assert os.environ['BIOTASKS_RUN_ID']==self.run and os.environ['IRIS_WORKER_ID']==os.environ['BIOTASKS_EXPECTED_WORKER']
        worker=os.environ['IRIS_WORKER_ID'];excluded=self.config['exclusions']
        assert worker not in excluded['excluded_worker_ids'] and worker.rsplit('-worker-',1)[0] not in excluded['excluded_worker_prefixes']
        assert not any(os.environ.get(k) for k in ('OPENROUTER_API_KEY','GH_TOKEN','GITHUB_TOKEN','CW_KEY_SECRET'))
        payload=json.loads((self.root/'payload.json').read_text())
        for name,value in payload['sha256'].items():assert sha(self.root/name)==value
        self.report.update(payload_sha256=payload['sha256'],worker_id=worker,different_worker_verified=True)
        assert self.config['resources']['cpus']==2 and self.config['resources']['memory_gib']==12
        assert self.config['resources']['controller_cpus']==0.5
        shutil.copyfile(self.root/'tasks.tar.gz',self.out/'input-package.tar.gz')
        self.checkpoint()

    def initialize_dependency(self,deadline):return True

    def controller_ready(self):pass

    def prerequisite(self,context,resources):
        self.report['bootstrap_build_started']=time.time()
        self.report['phase']='bootstrap_build_running';self.checkpoint()
        build=self.exec_logged('bootstrap-build.log',[self.controller,'python','/work/harbor-bin/docker','prefix-build',context],resources['bootstrap_build_timeout_seconds'])
        self.report.update(bootstrap_build_exit=build.returncode,bootstrap_build_finished=time.time())
        return build.returncode==0

    def work(self):
        pins=json.loads((self.root/'pins.json').read_text())
        resources=self.config['resources'];deadline=time.time()+resources['work_deadline_seconds']
        self.tools.mkdir();self.fetch(pins['docker_url'],self.tools/'docker.tgz',pins['docker_sha256'])
        with tarfile.open(self.tools/'docker.tgz') as tar:(self.tools/'docker').write_bytes(tar.extractfile('docker/docker').read())
        (self.tools/'docker').chmod(0o755)
        self.fetch(pins['compose_url'],self.tools/'docker-compose',pins['compose_sha256']);(self.tools/'docker-compose').chmod(0o755)
        absence={}
        for ref in self.config['original_image_refs']:
            result=self.docker('image','inspect',ref,check=False)
            assert result.returncode!=0 and 'No such image' in result.stderr
            absence[ref]=True
        self.report['original_image_absence']=absence
        if not self.initialize_dependency(deadline):
            self.report.update(stage='bootstrap_initialization_failed',controls_skipped='Recorded dependency prerequisite did not complete')
            for row in self.report['tasks']:row['state']='not_attempted_bootstrap_initialization_failure'
            self.checkpoint();return
        assert self.docker('volume','inspect',self.volume,check=False).returncode!=0
        self.report['resource_creation_started']=True;self.checkpoint()
        self.docker('volume','create','--label','biotasks.run='+self.run,self.volume)
        mountpoint=json.loads(self.docker('volume','inspect',self.volume).stdout)[0]['Mountpoint']
        self.docker('pull',pins['controller_image'],timeout=240)
        self.docker('create','--name',self.controller,'--cpus=0.5','--memory=4g','--memory-swap=4g',
            '--network=iris-egress','--label','biotasks.controller='+self.run,
            '-v','/var/run/docker.sock:/var/run/docker.sock','-v',self.volume+':/work','-v',self.volume+':'+mountpoint,'-w','/work',
            '-e','BIOTASKS_RUN_ID='+self.run,'-e','BIOTASKS_PHASE=controls','-e','BIOTASKS_SHARED_ROOT='+mountpoint,
            '-e','BIOTASKS_REAL_DOCKER=/work/real/docker','-e','DOCKER_CONFIG=/work/docker-config','-e','BIOTASKS29_BOUNDED_SUPERVISOR=1',
            pins['controller_image'],'sleep',str(resources['timeout_seconds']))
        self.created=True;self.docker('start',self.controller)
        self.docker('exec',self.controller,'mkdir','-p','/work/real','/work/evidence','/work/harbor-bin',
            '/work/docker-config/cli-plugins','/work/outputs','/work/infra','/work/jobs')
        controller_inputs=['pins.json','setup_controller.sh','run_existing_controls.py','control-plan.json','tasks.tar.gz','family.json']
        if self.config['mode']=='native_inline':controller_inputs.append('bootstrap-prefix.Dockerfile')
        for name in controller_inputs:
            self.docker('cp',str(self.root/name),self.controller+':/work/'+name)
        for source,dest in [(self.tools/'docker','/work/real/docker'),(self.tools/'docker-compose','/work/docker-config/cli-plugins/docker-compose'),
            (self.root/'docker_bridge.py','/work/harbor-bin/docker'),(self.root/'common.py','/work/harbor-bin/common.py')]:
            self.docker('cp',str(source),self.controller+':'+dest)
        self.docker('exec',self.controller,'chmod','+x','/work/harbor-bin/docker')
        # Verify all task bytes/modes before the trusted controller extracts them.
        unpack_task_archive(self.root/'tasks.tar.gz',self.config['task_bundle']['files'],None)
        self.docker('exec',self.controller,'tar','-xzf','/work/tasks.tar.gz','-C','/work')
        self.controller_ready()
        context='/work/outputs/'+self.config['id']+'/'+self.config['tasks'][0]['task']+'/environment'
        if not self.prerequisite(context,resources):
            self.report.update(stage='bootstrap_build_failed',controls_skipped='First common prerequisite build failed; no repeated task builds or controls')
            for row in self.report['tasks']:row['state']='not_attempted_bootstrap_failure'
            self.checkpoint()
            return
        self.report['phase']='setup_running';self.checkpoint()
        setup=self.exec_logged('setup.log',[self.controller,'bash','/work/setup_controller.sh'],resources['setup_timeout_seconds'])
        self.report['setup_exit']=setup.returncode;assert setup.returncode==0
        self.report['controls_started']=time.time()
        full_plan=json.loads((self.root/'control-plan.json').read_text())
        repo=full_plan['repositories'][0]
        assert repo['repo']==self.config['repo']
        for index,(task,row) in enumerate(zip(self.config['tasks'],self.report['tasks'],strict=True)):
            if time.time()+resources['bootstrap_build_timeout_seconds']+2*900+300>deadline:
                for remaining in self.report['tasks'][index:]:remaining.update(state='not_attempted_budget_reserve')
                break
            row.update(state='task_build_running',started=time.time());self.checkpoint()
            self.report['phase']='task_build_running';self.checkpoint()
            context='/work/outputs/'+self.config['id']+'/'+task['task']+'/environment'
            build=self.exec_logged(task['task']+'-build.log',['-e','CONTEXT_DIR='+context,
                self.controller,'python','/work/harbor-bin/docker','compose','build'],resources['bootstrap_build_timeout_seconds'])
            row.update(task_build_exit=build.returncode,task_build_finished=time.time())
            if build.returncode!=0:
                row.update(state='task_build_failed',finished=time.time());self.checkpoint();continue
            # Selection is orchestration data; original TaskSpec and helper stay unchanged.
            selected=next(t for t in repo['tasks'] if t['task']==task['task'])
            plan=dict(full_plan,repositories=[dict(repo,tasks=[selected])])
            path=self.root/'selected-control-plan.json';path.write_text(json.dumps(plan,indent=2)+'\n')
            row['control_plan_sha256']=sha(path)
            self.docker('cp',str(path),self.controller+':/work/control-plan.json')
            self.docker('cp',str(path),self.controller+':/work/infra/'+task['task']+'-control-plan.json')
            row.update(state='controls_running',controls_started=time.time());self.checkpoint()
            self.report['phase']='controls_running';self.checkpoint()
            control=self.exec_logged(task['task']+'-controller.log',['-e','PATH=/work/harbor-bin:/work/harbor066/bin:/usr/local/bin:/usr/bin:/bin',
                self.controller,'timeout','--kill-after=15s',str(max(1,int(deadline-time.time()))),'python','/work/run_existing_controls.py',
                '--repo',self.config['repo'],'--tasks-root','/work','--jobs',mountpoint+'/jobs/'+task['task'],
                '--evidence','/work/evidence/controls/'+task['task'],'--deadline',str(deadline),'--execute'],max(1,deadline-time.time()+30))
            row.update(state='controls_attempted',controls_exit=control.returncode,finished=time.time());self.checkpoint()
            if control.returncode!=0:
                for remaining in self.report['tasks'][index+1:]:remaining.update(state='not_attempted_prior_wrapper_failure')
                break
        self.report.update(stage='family_completed',controls_finished=time.time())
        self.checkpoint()

    def finish(self):
        if (self.tools/'docker').exists() and self.report.get('resource_creation_started'):
            try:
                ids=self.docker('ps','-aq','--filter','label=biotasks.run='+self.run).stdout.split()
                if ids:self.docker('rm','-f',*ids)
                if self.created:
                    self.docker('exec',self.controller,'tar','-czf','/work/evidence/control-artifacts.tar.gz','-C','/work','outputs','jobs','infra',timeout=120)
                    self.docker('cp',self.controller+':/work/evidence/.',str(self.out),timeout=120)
                    self.report['archive_copied']=True
                    base=self.docker('image','inspect',self.config['public_base_ref'],check=False)
                    if base.returncode==0:self.report['public_base_inspect']=json.loads(base.stdout)[0]
            except Exception as error:self.report['archive_error']=type(error).__name__+': '+str(error)[:200]
            # A failed copy must not destroy the only copy of task execution evidence.
            if self.created and not self.report.get('archive_copied'):
                self.report['cleanup_deferred']=dict(volume=self.volume,controller=self.controller,
                    reason='Execution evidence has not been copied; preserve owned volume before deletion')
                try:self.docker('stop','--time','10',self.controller)
                except Exception as error:self.report['stop_error']=type(error).__name__
            else:
                try:
                    from cleanup_owned import cleanup
                    self.report['cleanup']=cleanup(self.tools/'docker',self.run)
                except Exception as error:self.report['cleanup_error']=type(error).__name__+': '+str(error)[:200]
        elif self.report.get('payload_sha256') and not self.report.get('resource_creation_started'):
            self.report['cleanup']=dict(verified_no_creation=True,verified_empty=False,
                reason='Bound source code stopped before its first creation request; no deletion or daemon-empty claim')
        if self.tools.exists():shutil.rmtree(self.tools)
        self.report['finished']=time.time()
        self.report['output_sha256']={str(p.relative_to(self.out)):sha(p) for p in self.out.rglob('*') if p.is_file() and p.name!='result.json'}
        (self.out/'result.json').write_text(json.dumps(self.report,indent=2)+'\n')

    def execute(self):
        self.out.mkdir(parents=True,exist_ok=True)
        try:self.validate();self.work()
        except Exception as error:
            self.report.update(error_type=type(error).__name__,error=str(error)[:500],error_phase=self.report.get('phase'))
            if isinstance(error,subprocess.TimeoutExpired):
                self.report['stage']=self.report.get('phase','unknown')+'_timeout'
        finally:self.finish()
        print('BIOTASKS39_RESULT='+json.dumps(self.report),flush=True)
        cleanup=self.report.get('cleanup') or {}
        assert cleanup.get('verified_empty') or cleanup.get('verified_no_creation')


def main():
    root=Path(__file__).resolve().parent
    supervisor=Supervisor(root,Path(os.environ['IRIS_OUTPUT_DIR']),json.loads((root/'family.json').read_text()))
    def interrupted(sig,frame):raise RuntimeError('signal '+str(sig))
    signal.signal(signal.SIGTERM,interrupted);signal.signal(signal.SIGINT,interrupted)
    supervisor.execute()


if __name__=='__main__':main()
