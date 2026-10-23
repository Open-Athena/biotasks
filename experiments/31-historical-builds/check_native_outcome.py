"""Full native validator on compiled fixture; local adapter, no Docker or network."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import types

ROOT=Path(__file__).resolve().parent


def module(name,path,package=False):
    spec=importlib.util.spec_from_file_location(name,path,submodule_search_locations=[str(path.parent)] if package else None)
    value=importlib.util.module_from_spec(spec);sys.modules[name]=value;spec.loader.exec_module(value);return value


def main():
    provenance=json.loads((ROOT/'provenance.json').read_text())
    for row in provenance['files']:assert hashlib.sha256((ROOT/row['path']).read_bytes()).hexdigest()==row['sha256']
    for name,path in [('repo2rlenv',ROOT/'upstream'),('repo2rlenv.bootstrap',ROOT/'upstream/bootstrap'),('repo2rlenv.pipelines',ROOT/'upstream/pipelines')]:
        value=types.ModuleType(name);value.__path__=[str(path)];sys.modules[name]=value
    docker=module('repo2rlenv.bootstrap.docker',ROOT/'upstream/bootstrap/docker.py')
    module('repo2rlenv.log_parsers',ROOT/'upstream/log_parsers/__init__.py',True)
    original=module('original_validator',ROOT/'upstream/pipelines/pr_runtime_validate.py')
    module('repo2rlenv.pipelines.runtime_rebuild',ROOT/'candidate/pipelines/runtime_rebuild.py')
    candidate=module('candidate_validator',ROOT/'candidate/pipelines/pr_runtime_validate.py')
    rows=[]
    with tempfile.TemporaryDirectory(prefix='biotasks31-native-') as td:
        root=Path(td);repo=root/'workspace';repo.mkdir()
        env={**os.environ,'HOME':str(root),'GIT_CONFIG_NOSYSTEM':'1','GIT_CONFIG_GLOBAL':str(root/'gitconfig')}
        def run(command):return subprocess.run(command,cwd=repo,env=env,text=True,capture_output=True,timeout=10)
        def git(*args):
            result=run(['git',*args]);assert result.returncode==0,result.stderr;return result.stdout.strip()
        git('init','-q');git('config','user.name','Synthetic fixture');git('config','user.email','fixture@example.invalid')
        (repo/'value.c').write_text('int fixture_value(void) { return 1; }\n')
        (repo/'test_value.py').write_text('import ctypes, unittest\nclass ValueTests(unittest.TestCase):\n def test_fixed(self):\n  self.assertEqual(ctypes.CDLL("./fixture.so").fixture_value(),2)\n def test_stable(self):\n  self.assertGreaterEqual(ctypes.CDLL("./fixture.so").fixture_value(),1)\n')
        git('add','.');git('commit','-qm','Base fixture');base=git('rev-parse','HEAD')
        (repo/'value.c').write_text('int fixture_value(void) { return 2; }\n');patch=git('diff')+'\n'
        build='cc -shared -fPIC -O0 value.c -o fixture.so'
        for mode in ('original','candidate_disabled','rebuild','pre_build_failure','post_build_failure','invalid_test_patch'):
            git('reset','--hard',base);git('clean','-fdx')
            # Begin with an explicitly stale fixed-ref bootstrap binary.
            (repo/'value.c').write_text('int fixture_value(void) { return 2; }\n');assert run(['bash','-c',build]).returncode==0
            calls=[]
            class LocalSandbox:
                def exec(self,command,*,timeout=300):
                    start=time.monotonic()
                    result=run(['bash','-c',command.replace('/workspace',str(repo))])
                    row={'stage':'echo R2E_START_TEST_OUTPUT' in command,'exit_code':result.returncode,
                         'start_marker':'R2E_START_TEST_OUTPUT' in result.stdout.splitlines(),
                         'end_marker':'R2E_END_TEST_OUTPUT' in result.stdout.splitlines(),
                         'command_sha256':hashlib.sha256(command.encode()).hexdigest()}
                    calls.append(row)
                    return docker.ExecResult(result.returncode,result.stdout,result.stderr,time.monotonic()-start)
            validator=original if mode=='original' else candidate
            kwargs={}
            if mode not in ('original','candidate_disabled'):
                commands=[build]
                if mode=='pre_build_failure':commands=['false\necho MASKED_FAILURE']
                if mode=='post_build_failure':commands=["if grep -q 'return 2;' value.c; then exit 1; fi",build]
                kwargs['rebuild_cmds']=commands
            test_patch=''
            if mode=='invalid_test_patch':test_patch='diff --git a/nonexistent b/nonexistent\n--- a/nonexistent\n+++ b/nonexistent\n@@ -1 +1 @@\n-missing\n+new\n'
            outcome=validator.validate_pr(sandbox=LocalSandbox(),base_commit=base,patch=patch,test_patch=test_patch,
                test_cmds=['python3 -m unittest -v test_value'],language='python',timeout=10,**kwargs)
            stages=[c for c in calls if c['stage']]
            if mode=='rebuild':
                assert outcome.status=='verified'
                assert outcome.fail_to_pass==['test_value.ValueTests.test_fixed']
                assert outcome.pass_to_pass==['test_value.ValueTests.test_stable']
                assert len(stages)==2 and all(c['start_marker'] and c['end_marker'] for c in stages)
            elif mode in ('pre_build_failure','invalid_test_patch'):
                assert outcome.status=='failed' and outcome.reason=='pre stage incomplete or setup/rebuild failed'
                assert len(stages)==1 and not stages[0]['start_marker']
            elif mode=='post_build_failure':
                assert outcome.status=='failed' and outcome.reason=='post stage incomplete or setup/rebuild failed'
                assert len(stages)==2 and not stages[1]['start_marker']
            else:
                assert outcome.status=='failed' and not outcome.fail_to_pass
            rows.append({'mode':mode,'status':outcome.status,'reason':outcome.reason,
                         'f2p':outcome.fail_to_pass,'p2p':outcome.pass_to_pass,'stage_calls':stages})
        for key in ('status','reason','f2p','p2p','stage_calls'):assert rows[0][key]==rows[1][key]
    output={'scope':'Complete imported native validator and original parser dispatcher; actual compiled unittest fixture via local path adapter',
            'cases':rows,'all_assertions_passed':True,'default_disabled_outcome_and_commands_equal':True,
            'temporary_directory_removed':not root.exists(),'model_calls':0,
            'limits':['No full CLI/configuration construction or Docker execution',
                      'Local adapter remaps /workspace and uses bash -c instead of Docker login shell',
                      'No MACS or biological task recovery; no timeout cancellation claim']}
    (ROOT/'native-outcome-results.json').write_text(json.dumps(output,indent=2)+'\n')
    print(json.dumps({'cases':len(rows),'passed':True,'temporary_directory_removed':not root.exists()}))


if __name__=='__main__':main()
