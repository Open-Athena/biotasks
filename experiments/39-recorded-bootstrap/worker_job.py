"""Recorded dependency stage plus adopted original controls/archive/cleanup."""
import json
import os
from pathlib import Path
import signal
import time

from bootstrap_init import Initializer
from common import sha
from supervisor_base import Supervisor


class ReplaySupervisor(Supervisor):
    ALLOWED_MODES=('recorded_bootstrap_dependency',)

    def initialize_dependency(self,deadline):
        self.report.update(resource_creation_started=True,phase='recorded_bootstrap_initialization')
        self.checkpoint()
        initializer=Initializer(self.root,self.out/'bootstrap',self.tools/'docker',self.run,
            time.monotonic()+max(0,deadline-time.time()))
        ready=initializer.execute()
        self.report['bootstrap_replay']=initializer.report
        self.report['bootstrap_build_exit']=None
        self.checkpoint()
        return ready

    def controller_ready(self):
        self.docker('cp',str(self.root/'bootstrap-dependency.json'),self.controller+':/work/bootstrap-dependency.json')
        self.docker('cp',str(self.out/'bootstrap/bootstrap-replay.json'),self.controller+':/work/evidence/bootstrap-replay.json')

    def prerequisite(self,context,resources):
        descriptor=json.loads((self.root/'bootstrap-dependency.json').read_text())
        report=self.report['bootstrap_replay']
        assert report['stage']=='dependency_verified' and report['descriptor_sha256']==sha(self.root/'bootstrap-dependency.json')
        image=json.loads(self.docker('image','inspect',descriptor['dependency_ref']).stdout)[0]
        assert image['Id']==report['image_id'] and image['Config']['Labels']['biotasks.run']==self.run
        self.report.update(prerequisite_mode='recorded_bootstrap_dependency',bootstrap_dependency_image_id=image['Id'])
        self.checkpoint();return True


def main():
    root=Path(__file__).resolve().parent
    supervisor=ReplaySupervisor(root,Path(os.environ['IRIS_OUTPUT_DIR']),json.loads((root/'family.json').read_text()))
    def interrupted(sig,frame):raise RuntimeError('signal '+str(sig))
    signal.signal(signal.SIGTERM,interrupted);signal.signal(signal.SIGINT,interrupted)
    supervisor.execute()


if __name__=='__main__':main()
