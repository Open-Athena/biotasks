"""Exercise supervisor's negative-build stop with inert Docker/process substitutes."""
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
import types
from unittest import mock

ROOT=Path(__file__).resolve().parent
RUN='biotasks37-ohif-5996-inline-001'


def main():
    with tempfile.TemporaryDirectory(prefix='failure-stop-',dir=ROOT/'inputs-private') as td:
        work=Path(td);output=work/'out';output.mkdir()
        for name,data in [('pins.json',{'docker_url':'fixture-docker','docker_sha256':'unused',
                'compose_url':'fixture-compose','compose_sha256':'unused','controller_image':'fixture-image'}),
            ('cold-worker-inputs.json',{'original_worker_state_refs':['old:image'],'public_base_ref':'node:22-slim','base_commit':'a'*40}),
            ('cold-payload.json',{'sha256':{}}),('original-workers.json',{'excluded_worker_ids':['old-worker-0']})]:
            (work/name).write_text(json.dumps(data))
        environment=dict(BIOTASKS_RUN_ID=RUN,IRIS_OUTPUT_DIR=str(output),IRIS_WORKER_ID='fresh-worker-0',
            BIOTASKS_EXPECTED_WORKER='fresh-worker-0')
        with mock.patch.dict(os.environ,environment):
            spec=importlib.util.spec_from_file_location('supervisor_fixture',ROOT/'cold_worker_job.py')
            module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        module.ROOT=work
        docker_calls=[];process_calls=[];cleanup_calls=[]
        def docker(*args,**kwargs):
            docker_calls.append(list(args))
            result=subprocess.CompletedProcess(args,0,stdout='',stderr='')
            if args[:2]==('image','inspect'):
                result.returncode=1;result.stdout='[]';result.stderr='Error: No such image'
            if args[:2]==('volume','inspect'):
                if kwargs.get('check') is False:result.returncode=1
                else:result.stdout=json.dumps([{'Mountpoint':'/fixture-volume'}])
            return result
        def fetch(url,path,sha,maximum):
            if path.suffix=='.tgz':
                with tarfile.open(path,'w:gz') as tar:
                    member=tarfile.TarInfo('docker/docker');member.size=7;tar.addfile(member,io.BytesIO(b'fixture'))
            else:path.write_bytes(b'fixture')
        def run(command,**kwargs):
            process_calls.append(command)
            assert command[-2:]==['compose','build'], 'No setup, control or repeated build permitted after failure'
            return subprocess.CompletedProcess(command,17)
        cleanup=types.ModuleType('cleanup_owned')
        def clean(binary,run_id):
            cleanup_calls.append(run_id);return dict(verified_empty=True,remaining={})
        cleanup.cleanup=clean
        with mock.patch.object(module,'docker',docker),mock.patch.object(module,'fetch',fetch),\
             mock.patch.object(module.subprocess,'run',run),mock.patch.object(module.signal,'signal'),\
             mock.patch.dict(sys.modules,{'cleanup_owned':cleanup}),mock.patch.dict(os.environ,environment):
            module.main()
        result=json.loads((output/'control-result.json').read_text())
        assert len(process_calls)==1 and cleanup_calls==[RUN]
        assert result['native_build_exit']==17 and result['scientific_stage']=='native_image_build_failed'
        assert 'controls_started' not in result and result['controls_skipped']
        assert result['archive_copied'] and result['cleanup']['verified_empty']
        assert not (work/'control-tools').exists()
        report=dict(simulated_build_failure_stops_before_setup_and_controls=True,
            build_invocations=1,cleanup_invocations=1,owned_fixture_directory_removed_on_exit=True,
            actual_docker_commands=0,actual_model_calls=0,
            supervisor_sha256=hashlib.sha256((ROOT/'cold_worker_job.py').read_bytes()).hexdigest())
    (ROOT/'failure-stop-check.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report))


if __name__=='__main__':main()
