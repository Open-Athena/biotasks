"""Real pytest/Bash/Git completion checks and standalone exported grading.

Uses only a small synthetic repository. No network, biological inputs, model,
remote worker, or original task reward is involved.
"""
import ast
from dataclasses import dataclass
import importlib.util
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys
import tempfile
from check_completion import load

ROOT=Path(__file__).resolve().parent

@dataclass
class Result:
    stdout:str
    stderr:str
    exit_code:int
    def truncated(self,max_chars):return (self.stdout+'\n'+self.stderr)[-max_chars:]

class Shell:
    def __init__(self,root,mode='normal',fixed=False):self.root=root;self.mode=mode;self.fixed=fixed;self.calls=[];self.results=[]
    def exec(self,command,timeout):
        env={**os.environ,'FIXTURE_FIXED':str(int(self.fixed or bool(self.calls))), 'FIXTURE_MODE':self.mode,'PYTEST_DISABLE_PLUGIN_AUTOLOAD':'1','GIT_CONFIG_GLOBAL':str(self.root.parent/'fixture.gitconfig'),'GIT_CONFIG_NOSYSTEM':'1'}
        p=subprocess.run(['bash','-lc',command.replace('/workspace',str(self.root))],env=env,capture_output=True,text=True,timeout=min(timeout,30),check=False)
        codes=[line for line in p.stdout.splitlines() if line.startswith('R2E_TEST_EXIT_CODE=')]
        self.calls.append({'outer_exit':p.returncode,'inner_exit_lines':codes,'start_marker':'R2E_START_TEST_OUTPUT' in p.stdout.splitlines()})
        result=Result(p.stdout,p.stderr,p.returncode);self.results.append(result);return result


def module():
    m=load('strict_pytest_candidate',ROOT/'candidate-pytest-completion/pr_runtime_validate.py')
    src=ast.parse((ROOT/'upstream/log_parsers/__init__.py').read_text())
    fn=next(n for n in src.body if isinstance(n,ast.FunctionDef) and n.name=='_detect_runner')
    ns={'re':re};exec(compile(ast.Module(body=[fn],type_ignores=[]),'original_runner_detection','exec'),ns)
    m._detect_runner=ns['_detect_runner']
    spec=importlib.util.spec_from_file_location('strict_pytest_parser',ROOT/'candidate-pytest-completion/pytest_parser.py')
    parser=importlib.util.module_from_spec(spec);spec.loader.exec_module(parser)
    m.parse_logs=lambda cmds,log,language=None:parser.parse_pytest(log)
    return m


def main():
    m=module();rows=[];exports=[]
    with tempfile.TemporaryDirectory(prefix='biotasks32-pytest-completion-') as temp:
        root=Path(temp);repo=root/'repo';repo.mkdir();(repo/'tests').mkdir()
        def git(*args):return subprocess.check_output(['git','-C',str(repo),*args],text=True,stderr=subprocess.DEVNULL).strip()
        git('init','-q');git('config','user.email','fixture@example.invalid');git('config','user.name','Fixture')
        (repo/'tests/test_case.py').write_text('''import os, signal

def test_fix():
    assert os.environ["FIXTURE_FIXED"] == "1"

def test_stable():
    assert 2 + 2 == 4

def test_stop():
    mode = os.environ["FIXTURE_MODE"]
    if mode == "interrupt":
        raise KeyboardInterrupt()
    if mode == "exit124":
        os._exit(124)
    if mode == "killed":
        os.kill(os.getpid(), signal.SIGKILL)
''')
        git('add','tests/test_case.py');git('commit','-qm','fixture');ref=git('rev-parse','HEAD')
        cmds=[shlex.quote(sys.executable)+' -m pytest -v -s --color=yes tests/test_case.py']
        good=None
        for label,mode,base,patch in [('complete','normal',ref,''),('keyboard_interrupt','interrupt',ref,''),('runner_exit124','exit124',ref,''),('runner_killed','killed',ref,''),('invalid_base','normal','0'*40,''),('invalid_test_patch','normal',ref,'not a patch')]:
            sb=Shell(repo,mode)
            result=m.validate_pr(sandbox=sb,base_commit=base,patch='',test_patch=patch,test_cmds=cmds,language='python')
            expected='verified' if label=='complete' else 'failed'
            assert result.status==expected,(label,result)
            if label=='complete':
                assert result.fail_to_pass==['tests/test_case.py::test_fix']
                assert set(result.pass_to_pass)=={'tests/test_case.py::test_stable','tests/test_case.py::test_stop'}
                assert '\x1b[' in result.post_log
                assert sb.calls[0]['inner_exit_lines']==['R2E_TEST_EXIT_CODE=1'] and sb.calls[1]['inner_exit_lines']==['R2E_TEST_EXIT_CODE=0']
                good=result
            else:
                assert len(sb.calls)==1 and not result.fail_to_pass and not result.pass_to_pass
            rows.append({'case':label,'status':result.status,'reason':result.reason,'f2p':result.fail_to_pass,'p2p':result.pass_to_pass,'calls':sb.calls})
        sb=Shell(repo)
        unsupported=m.validate_pr(sandbox=sb,base_commit=ref,patch='',test_patch='',test_cmds=['cargo test'],language='rust')
        assert unsupported.status=='skipped' and not sb.calls
        # Protocol integrity checks operate on controlled records, separate from
        # the real runner cases above.
        valid='R2E_START_TEST_OUTPUT\nx\nR2E_TEST_EXIT_CODE=0\nR2E_END_TEST_OUTPUT\n'
        malformed=[valid.replace('R2E_TEST_EXIT_CODE=0\n',''),valid+ 'R2E_END_TEST_OUTPUT\n',valid.replace('R2E_START_TEST_OUTPUT','TEMP').replace('R2E_END_TEST_OUTPUT','R2E_START_TEST_OUTPUT').replace('TEMP','R2E_END_TEST_OUTPUT'),valid.replace('R2E_TEST_EXIT_CODE=0','R2E_TEST_EXIT_CODE=5')]
        assert m._pytest_stage_completed(Result(valid,'',0))
        assert all(not m._pytest_stage_completed(Result(s,'',0)) for s in malformed)
        assert not m._pytest_stage_completed(Result(valid,'',124))
        f2p=root/'f2p.json';p2p=root/'p2p.json'
        f2p.write_text(json.dumps(good.fail_to_pass));p2p.write_text(json.dumps(good.pass_to_pass))
        for label,mode,fixed,code,expected in [('nop','normal',False,1,0.0),('oracle','normal',True,0,1.0),('interrupt','interrupt',True,2,0.0),('timeout_exit','exit124',True,124,0.0),('killed','killed',True,137,0.0)]:
            sb=Shell(repo,mode,fixed)
            result=sb.exec(m._build_stage_script(ref,apply_patch=None,apply_test_patch=None,test_cmds=cmds),30)
            assert sb.calls[0]['inner_exit_lines']==['R2E_TEST_EXIT_CODE='+str(code)], (label,sb.calls,result.stderr[-500:])
            log=root/(label+'.log');log.write_text(result.stdout)
            out=root/('grade-'+label)
            argv=[sys.executable,str(ROOT/'candidate-pytest-completion/_pr_runtime_verifier.py'),'--log',str(log),'--f2p',str(f2p),'--p2p',str(p2p),'--runner','pytest','--exit-code',str(code),'--out-dir',str(out)]
            subprocess.run(argv,capture_output=True,text=True,timeout=15,check=True)
            previous=root/('previous-grade-'+label)
            old_argv=list(argv);old_argv[1]=str(ROOT/'candidate/_pr_runtime_verifier.py');old_argv[-1]=str(previous)
            subprocess.run(old_argv,capture_output=True,text=True,timeout=15,check=True)
            previous_reward=float((previous/'reward.txt').read_text())
            detail=json.loads((out/'reward-details.json').read_text());reward=float((out/'reward.txt').read_text())
            assert reward==expected,(label,detail)
            if code not in (0,1):assert previous_reward>0 and detail['parse_status']=='incomplete_pytest_exit' and not detail['resolved'] and not detail['command_resolved']
            exports.append({'case':label,'test_exit':code,'previous_sgr_only_reward':previous_reward,'reward':reward,'parse_status':detail['parse_status'],'resolved':detail['resolved'],'command_resolved':detail['command_resolved']})
    assert not root.exists()
    report={'scope':'Actual pytest/Bash/Git synthetic repository and standalone export verifier; not biological recovery or full Harbor validation','native_cases':rows,'export_cases':exports,'unsupported_runner_skipped':True,'malformed_protocol_cases_rejected':5,'temporary_directory_removed':True,'model_calls':0,'remote_jobs':0,'pytest_version':__import__('pytest').__version__}
    (ROOT/'pytest-completion-results.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'native_cases':len(rows),'export_cases':len(exports),'all_passed':True,'temporary_directory_removed':True}))

if __name__=='__main__':main()
