"""One bounded native Harbor infrastructure probe, no model/generation calls."""
import json
import os
from pathlib import Path
import shutil
import signal
import tarfile
import time

from common import sha,unpack_task_archive
from supervisor_base import Supervisor


class Diagnostic(Supervisor):
    def __init__(self,root,out,config):
        # The generic supervisor initializes biological task statuses. This
        # infrastructure probe has cases instead; its driver records outcomes.
        super().__init__(root,out,dict(config,tasks=[]))
        self.report.pop('tasks')

    def validate(self):
        assert self.config['mode']=='harbor_timeout_diagnostic'
        assert os.environ['BIOTASKS_RUN_ID']==self.run and os.environ['IRIS_WORKER_ID']==os.environ['BIOTASKS_EXPECTED_WORKER']
        assert not any(os.environ.get(k) for k in ['OPENROUTER_API_KEY','GH_TOKEN','GITHUB_TOKEN','CW_KEY_ID','CW_KEY_SECRET','HF_TOKEN'])
        payload=json.loads((self.root/'payload.json').read_text())
        for name,value in payload['sha256'].items():assert sha(self.root/name)==value
        r=self.config['resources'];assert r['cpus']==2 and r['memory_gib']==12 and r['controller_cpus']==0.5
        self.report.update(payload_sha256=payload['sha256'],worker_id=os.environ['IRIS_WORKER_ID'],worker_constraint_verified=True,
            kind='native_harbor_infrastructure_fixture',original_tasks_changed=False)
        shutil.copyfile(self.root/'tasks.tar.gz',self.out/'input-package.tar.gz');self.checkpoint()

    def work(self):
        pins=json.loads((self.root/'pins.json').read_text());r=self.config['resources'];deadline=time.time()+r['work_deadline_seconds']
        self.tools.mkdir();self.fetch(pins['docker_url'],self.tools/'docker.tgz',pins['docker_sha256'])
        with tarfile.open(self.tools/'docker.tgz') as archive:(self.tools/'docker').write_bytes(archive.extractfile('docker/docker').read())
        (self.tools/'docker').chmod(0o755)
        self.fetch(pins['compose_url'],self.tools/'docker-compose',pins['compose_sha256']);(self.tools/'docker-compose').chmod(0o755)
        for ref in [c['image_ref'] for c in self.config['cases']]:
            found=self.docker('image','inspect',ref,check=False);assert found.returncode!=0 and 'No such image' in found.stderr
        assert self.docker('volume','inspect',self.volume,check=False).returncode!=0
        self.report['resource_creation_started']=True;self.report['phase']='owned_volume_creation';self.checkpoint()
        self.docker('volume','create','--label','biotasks.run='+self.run,self.volume)
        mountpoint=json.loads(self.docker('volume','inspect',self.volume).stdout)[0]['Mountpoint']
        self.docker('pull',pins['controller_image'],timeout=240)
        self.docker('create','--name',self.controller,'--cpus=0.5','--memory=4g','--memory-swap=4g','--network=iris-egress',
            '--label','biotasks.controller='+self.run,'-v','/var/run/docker.sock:/var/run/docker.sock',
            '-v',self.volume+':/work','-v',self.volume+':'+mountpoint,'-w','/work',
            '-e','BIOTASKS_RUN_ID='+self.run,'-e','BIOTASKS_SHARED_ROOT='+mountpoint,
            '-e','DOCKER_CONFIG=/work/docker-config',pins['controller_image'],'sleep',str(r['timeout_seconds']))
        self.created=True;self.docker('start',self.controller)
        self.docker('exec',self.controller,'mkdir','-p','/work/real','/work/evidence','/work/docker-config/cli-plugins','/work/outputs','/work/jobs','/work/infra')
        for name in ['pins.json','tasks.tar.gz','family.json','setup_controller.sh','probe_driver.py','package-source-pins.json',
            'harbor-0.6.6-py3-none-any.whl','tenacity-9.2.1-py3-none-any.whl']:
            self.docker('cp',str(self.root/name),self.controller+':/work/'+name)
        for src,dest in [(self.tools/'docker','/work/real/docker'),(self.tools/'docker-compose','/work/docker-config/cli-plugins/docker-compose')]:self.docker('cp',str(src),self.controller+':'+dest)
        self.docker('exec',self.controller,'mkdir','-p','/work/bin')
        self.docker('exec',self.controller,'ln','-s','/work/real/docker','/work/bin/docker')
        unpack_task_archive(self.root/'tasks.tar.gz',self.config['task_bundle']['files'],None)
        self.docker('exec',self.controller,'tar','-xzf','/work/tasks.tar.gz','-C','/work')
        self.report['phase']='owned_fixture_image_builds';self.checkpoint()
        self.docker('pull',self.config['public_base_ref'],timeout=240)
        base=json.loads(self.docker('image','inspect',self.config['public_base_ref']).stdout)[0]
        assert base['Id']==self.config['expected_public_base_id'];self.report['public_base_before']=dict(Id=base['Id'],RepoDigests=base['RepoDigests'])
        self.docker('create','--name',self.run+'-base-reference','--cpus=0.05','--memory=64m','--memory-swap=64m','--network=none',
            '--label','biotasks.controller='+self.run,self.config['public_base_ref'],'true')
        self.report['stopped_public_base_reference_created']=True
        self.report['public_base_reference_started']=False
        self.report['fixture_image_builds']=[]
        for case in self.config['cases']:
            assert time.time()+120+300<deadline
            context=self.root/'image-context'/case['name'];context.mkdir(parents=True)
            recipe=context/'Dockerfile'
            recipe.write_text('FROM '+self.config['public_base_ref']+'\nLABEL biotasks.run='+self.run+'\nLABEL biotasks.fixture='+case['name']+'\n')
            with (self.out/(case['name']+'-image-build.log')).open('w') as log:
                import subprocess
                result=subprocess.run([str(self.tools/'docker'),'build','--force-rm','--cpu-period=100000','--cpu-quota=150000','--memory=6g',
                    '--memory-swap=6g','--network=none','--label','biotasks.run='+self.run,'--tag',case['image_ref'],'-f',str(recipe),str(context)],
                    stdout=log,stderr=subprocess.STDOUT,timeout=120,check=False,env=dict(os.environ,DOCKER_BUILDKIT='0'))
            build=dict(case=case['name'],exit_code=result.returncode,dockerfile_sha256=sha(recipe),dockerfile_text=recipe.read_text(),image_ref=case['image_ref'])
            self.report['fixture_image_builds'].append(build);self.checkpoint()
            assert result.returncode==0
            image=json.loads(self.docker('image','inspect',case['image_ref']).stdout)[0]
            assert image['Config']['Labels']['biotasks.run']==self.run and image['RootFS']==base['RootFS'] and image['Config']['Env']==base['Config']['Env']
            build.update(image_id=image['Id'],metadata_only=True)
        assert time.time()+r['setup_timeout_seconds']+300<deadline
        self.report['phase']='controller_setup';self.checkpoint()
        setup=self.exec_logged('setup.log',[self.controller,'bash','/work/setup_controller.sh'],r['setup_timeout_seconds'])
        self.report['setup_exit']=setup.returncode;self.checkpoint();assert setup.returncode==0
        assert time.time()+240+300<deadline
        self.report['phase']='native_fixture_cases';self.checkpoint()
        probe=self.exec_logged('probe-driver.log',['-e','PATH=/work/bin:/usr/local/bin:/usr/bin:/bin',self.controller,
            '/work/harbor066/bin/python','/work/probe_driver.py'],240)
        self.report['probe_driver_exit']=probe.returncode
        after=json.loads(self.docker('image','inspect',self.config['public_base_ref']).stdout)[0]
        assert after['Id']==base['Id'];self.report['shared_public_base_preserved']=True
        self.report.update(stage='native_probe_returned',probe_finished=time.time());self.checkpoint()

    def finish(self):
        context=self.root/'image-context'
        if context.exists():shutil.rmtree(context)
        self.report['build_context_removed']=not context.exists()
        super().finish()

def main():
    root=Path(__file__).resolve().parent
    supervisor=Diagnostic(root,Path(os.environ['IRIS_OUTPUT_DIR']),json.loads((root/'family.json').read_text()))
    def interrupted(sig,frame):raise RuntimeError('signal '+str(sig))
    signal.signal(signal.SIGTERM,interrupted);signal.signal(signal.SIGINT,interrupted)
    supervisor.execute()


if __name__=='__main__':main()
