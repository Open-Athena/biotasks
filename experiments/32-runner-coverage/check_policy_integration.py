"""Complete-package config/writer and controlled run-loop wiring; no real runner."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import tomllib
from types import SimpleNamespace

ROOT=Path(__file__).resolve().parent
PRIOR=ROOT.parents[2]/'31/experiments/31-historical-builds'

def main():
    acquired=json.loads((PRIOR/'package-acquisition.json').read_text())
    source=PRIOR/'inputs-private/upstream-package'
    for row in acquired['files']:
        assert hashlib.sha256((source/row['path']).read_bytes()).hexdigest()==row['sha256']
    blocked=[]
    with tempfile.TemporaryDirectory(prefix='biotasks32-policy-') as td:
        root=Path(td);checkout=root/'package';shutil.copytree(source,checkout)
        subprocess.run(['git','apply',str(ROOT/'pytest-target-policy.patch')],cwd=checkout,check=True,capture_output=True,timeout=5)
        manifest=json.loads((ROOT/'policy-integration-manifest.json').read_text())
        for rel,digest in manifest['files'].items():
            assert hashlib.sha256((checkout/'src/repo2rlenv'/rel).read_bytes()).hexdigest()==digest
        def audit(event,args):
            if event in ('socket.connect','socket.getaddrinfo','subprocess.Popen','os.system'):
                blocked.append(event);raise AssertionError('Unexpected external operation: '+event)
        sys.addaudithook(audit)
        sys.path[:0]=[str(checkout/'src'),str(PRIOR/'inputs-private/check-deps')]
        from repo2rlenv.config import load_generation_input
        from repo2rlenv.cli import _parse_pipeline_opts
        from repo2rlenv.spec.options import parse_options
        from repo2rlenv.pipelines import PIPELINES
        from repo2rlenv.bootstrap.spec import BootstrapResult,LanguageHint
        from repo2rlenv.github import PullRequestSummary
        from repo2rlenv.emitter.harbor import write_harbor_task
        from repo2rlenv.pipelines import pr_runtime as module
        from repo2rlenv.pipelines import pr_runtime_validate as validator
        from pydantic import ValidationError
        assert str(module.__file__).startswith(str(checkout))
        command='cd /workspace && python -m pytest -v mne/'
        boot=BootstrapResult(image_digest='sha256:'+'0'*64,image_tag='fixture:local',language=LanguageHint.PYTHON,
            repo='fixture/repo',ref='a'*40,rebuild_cmds=[],test_cmds=[command],smoke_passed=True,iterations=0,build_time_sec=0,llm_provider='none')
        pr=PullRequestSummary(number=1,title='Fix fixture output',body='The returned value is incorrect.',state='merged',merged_at='2026-01-01T00:00:00Z',base_ref='main',base_sha='a'*40,head_sha='b'*40,is_draft=False,url='https://github.com/fixture/repo/pull/1',changed_files=['value.py','mne/tests/test_value.py'])
        testpatch='diff --git a/mne/tests/test_old.py b/mne/tests/test_old.py\ndeleted file mode 100644\n--- a/mne/tests/test_old.py\n+++ /dev/null\n'+'diff --git a/mne/tests/test_value.py b/mne/tests/test_value.py\n--- a/mne/tests/test_value.py\n+++ b/mne/tests/test_value.py\n@@ -0,0 +1 @@\n+def test_new(): pass\n'
        sourcepatch='diff --git a/value.py b/value.py\n--- a/value.py\n+++ b/value.py\n@@ -1 +1 @@\n-return 0\n+return 1\n'
        rows=[]
        for name,flags in [('default',[]),('enabled',['literal_pytest_changed_files=true']),('disabled',['literal_pytest_changed_files=false'])]:
            config=root/(name+'.json');config.write_text(json.dumps({'repo':{'url':'fixture/repo','access':'public'},'pipeline':{'name':'pr_runtime','options':_parse_pipeline_opts(flags)},'output':{'destination':str(root/'output'),'org':'fixture','dataset_name':'fixture'}}))
            spec=load_generation_input(config);options=parse_options(spec.pipeline.name,spec.pipeline.options)
            pipeline=PIPELINES[spec.pipeline.name](spec,options,boot)
            selected,decisions=pipeline._test_selection(testpatch)
            expected='cd /workspace && python -m pytest -v mne/tests/test_value.py' if name=='enabled' else command
            assert selected==[expected]
            assert bool(decisions)==(name=='enabled')
            task=pipeline._build_task(pr,sourcepatch,testpatch,fail_to_pass=['mne/tests/test_value.py::test_new'],pass_to_pass=[],validation_status='verified')
            assert expected in task.test_script
            meta=task.repo2env['pr_runtime'];assert ('test_selection_decisions' in meta)==(name=='enabled')
            emitted=write_harbor_task(task,root/name)
            assert tomllib.loads((emitted/'task.toml').read_text())['metadata']['repo2env']['pr_runtime']==meta
            assert (emitted/'tests/test.sh').read_text()==task.test_script
            rows.append({'case':name,'commands':selected,'writer_metadata_verified':True})
        # Exercise actual run loop with deterministic provider/validator fixtures.
        pipeline=PIPELINES[spec.pipeline.name](spec,parse_options('pr_runtime',{'literal_pytest_changed_files':True}),boot)
        pipeline._pre_filter=lambda pr:None
        pipeline._lite_filter=lambda pr,patch:None
        module.resolve_repo_token=lambda *a:None
        module.provider_for=lambda *a:SimpleNamespace(list_merged_prs=lambda *a,**kw:[pr],fetch_pr_diff=lambda *a,**kw:sourcepatch+testpatch)
        captured=[];starts=[];cleanups=[]
        pipeline._start_validation_sandbox=lambda:(starts.append(True) or SimpleNamespace(cleanup=lambda:cleanups.append(True)))
        validator.validate_pr=lambda **kw:(captured.append(kw['test_cmds']) or SimpleNamespace(fail_to_pass=['mne/tests/test_value.py::test_new'],pass_to_pass=[],status='verified',reason='fixture'))
        result=pipeline.run(root/'controlled-run')
        assert result.emitted==1 and captured==[['cd /workspace && python -m pytest -v mne/tests/test_value.py']]
        assert len(starts)==len(cleanups)==1
        # Unsupported selection skips before a sandbox and cannot export even in debug mode.
        boot.test_cmds=['pytest -v | tee results.log']
        skipped=[]
        for skip in (False,True):
            pipeline.options.skip_validation=skip
            result=pipeline.run(root/('unsupported-'+str(skip)))
            assert result.emitted==0 and result.skip_reasons=={'unsupported_pytest_targeting':1}
            skipped.append({'skip_validation':skip,'skips':result.skip_reasons})
        assert len(starts)==1
        try:pipeline._build_task(pr,sourcepatch,testpatch,fail_to_pass=[],pass_to_pass=[],validation_status='skipped')
        except ValueError as exc:assert str(exc).startswith('unsupported_pytest_targeting:')
        else:raise AssertionError('Unsupported direct task construction accepted')
        try:parse_options('pr_runtime',{'literal_pytest_changed_file':True})
        except ValidationError:pass
        else:raise AssertionError('Unknown option accepted')
        assert not blocked
    out={'scope':'Complete-package configuration/writer and actual run-loop routing with provider/sandbox/validator fixtures',
        'cases':rows,'controlled_native_commands':captured,'unsupported_skips':skipped,'unsupported_direct_build_rejected':True,
        'unknown_option_rejected':True,'external_operations_attempted':blocked,'temporary_directory_removed':not root.exists(),
        'model_calls':0,'remote_jobs':0,'limits':['No Docker or biological execution','Validator fixture proves wiring, not test outcomes','Existing dependency environment, not upstream locked environment','Deleted-path selection is part of enabled intervention only']}
    (ROOT/'policy-integration-results.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out))

if __name__=='__main__':main()
