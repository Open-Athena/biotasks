"""Pinned complete-package imports, real config/options, constructor and task writer.

No generation/bootstrap/solver is invoked. Network and subprocess calls are
blocked after applying the research patch to a disposable source copy.
"""
import hashlib
import importlib.metadata
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import tomllib

ROOT=Path(__file__).resolve().parent


def main():
    acquired=json.loads((ROOT/'package-acquisition.json').read_text())
    source=ROOT/'inputs-private/upstream-package'
    for row in acquired['files']:assert hashlib.sha256((source/row['path']).read_bytes()).hexdigest()==row['sha256']
    blocked=[]
    with tempfile.TemporaryDirectory(prefix='biotasks31-package-') as td:
        root=Path(td);checkout=root/'package';shutil.copytree(source,checkout)
        subprocess.run(['git','apply',str(ROOT/'historical-rebuild.patch')],cwd=checkout,check=True,capture_output=True,timeout=5)
        for rel in ('spec/options.py','pipelines/pr_runtime.py','pipelines/pr_runtime_validate.py','pipelines/runtime_rebuild.py'):
            assert (checkout/'src/repo2rlenv'/rel).read_bytes()==(ROOT/'candidate'/rel).read_bytes()
        def audit(event,args):
            if event in ('socket.connect','socket.getaddrinfo','subprocess.Popen','os.system'):
                blocked.append(event);raise AssertionError('Integration check attempted external operation: '+event)
        sys.addaudithook(audit)
        sys.path[:0]=[str(checkout/'src'),str(ROOT/'inputs-private/check-deps')]
        from repo2rlenv.config import load_generation_input
        from repo2rlenv.cli import _parse_pipeline_opts
        from repo2rlenv.spec.options import parse_options
        from repo2rlenv.pipelines import PIPELINES
        from repo2rlenv.bootstrap.spec import BootstrapResult,LanguageHint
        from repo2rlenv.github import PullRequestSummary
        from repo2rlenv.emitter.harbor import write_harbor_task
        from pydantic import ValidationError
        assert str(sys.modules['repo2rlenv'].__file__).startswith(str(checkout))
        boot=BootstrapResult(image_digest='sha256:'+'0'*64,image_tag='fixture:local',language=LanguageHint.PYTHON,
            repo='fixture/repo',ref='a'*40,rebuild_cmds=['cc -shared -fPIC value.c -o fixture.so'],
            test_cmds=['python -m unittest -v test_value'],smoke_passed=True,iterations=0,build_time_sec=0,llm_provider='none')
        pr=PullRequestSummary(number=1,title='Synthetic fixture',body='The returned value is incorrect.',state='merged',merged_at='2026-01-01T00:00:00Z',base_ref='main',base_sha='a'*40,head_sha='b'*40,is_draft=False,url='https://github.com/fixture/repo/pull/1',changed_files=['value.c','test_value.py'])
        rows=[]
        for name,flags in [('default',[]),('enabled',['replay_bootstrap_rebuild=true']),('disabled',['replay_bootstrap_rebuild=false'])]:
            raw={'repo':{'url':'fixture/repo','access':'public'},'pipeline':{'name':'pr_runtime','options':_parse_pipeline_opts(flags)},
                 'output':{'destination':str(root/'output'),'org':'fixture','dataset_name':'fixture'}}
            config=root/f'{name}.json';config.write_text(json.dumps(raw))
            spec=load_generation_input(config)
            options=parse_options(spec.pipeline.name,spec.pipeline.options,recipe=spec.pipeline.recipe)
            pipeline=PIPELINES[spec.pipeline.name](spec,options,boot)
            enabled=name=='enabled'
            assert options.replay_bootstrap_rebuild==enabled
            assert pipeline.rebuild_cmds==(boot.rebuild_cmds if enabled else None)
            if enabled:assert pipeline.rebuild_cmds is not boot.rebuild_cmds
            task=pipeline._build_task(pr,'','',fail_to_pass=['test_value.ValueTests.test_fixed'],pass_to_pass=['test_value.ValueTests.test_stable'],validation_status='verified')
            metadata=task.repo2env['pr_runtime']
            assert ('rebuild_cmds' in metadata)==enabled
            if enabled:
                assert metadata['rebuild_cmds']==boot.rebuild_cmds and metadata['rebuild_stage']=='after_patches_before_tests'
                assert 'cc -shared -fPIC value.c -o fixture.so' in task.test_script
            else:assert 'cc -shared -fPIC value.c -o fixture.so' not in task.test_script
            emitted=write_harbor_task(task,root/name)
            config_toml=tomllib.loads((emitted/'task.toml').read_text())
            stored=config_toml['metadata']['repo2env']['pr_runtime']
            assert stored==metadata
            assert (emitted/'tests/test.sh').read_text()==task.test_script
            assert (emitted/'tests/f2p.json').exists() and (emitted/'tests/verifier.py').exists()
            rows.append({'case':name,'enabled':enabled,'constructor_matches':True,'export_metadata_matches':True,'written_script_matches':True})
        boot.rebuild_cmds=[]
        try:PIPELINES['pr_runtime'](spec,parse_options('pr_runtime',{'replay_bootstrap_rebuild':True}),boot)
        except ValueError as error:assert 'requires recorded bootstrap rebuild_cmds' in str(error)
        else:raise AssertionError('Missing rebuild commands must fail')
        try:parse_options('pr_runtime',{'replay_bootstrap_rebulid':True})
        except ValidationError:pass
        else:raise AssertionError('Unknown option silently accepted')
        assert not blocked
        versions={p:importlib.metadata.version(p) for p in ('pydantic','PyYAML','rich','tomli-w')}
    result={'scope':'Complete patched upstream package imported; CLI option parser, configuration loader, registered constructor, task builder and actual Harbor writer',
            'revision':acquired['revision'],'cases':rows,'missing_recorded_commands_rejected':True,'unknown_option_rejected':True,
            'external_operations_attempted':blocked,'temporary_directory_removed':not root.exists(),'dependency_versions':versions,
            'python':sys.version.split()[0],'model_calls':0,
            'limits':['No CLI generate/bootstrap execution, Docker or biological repo validation',
                      'Synthetic task metadata and scripts were emitted, not executed in Harbor',
                      'Existing check environment plus isolated tomli-w; not upstream full locked dependency environment']}
    (ROOT/'package-integration-results.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))


if __name__=='__main__':main()
