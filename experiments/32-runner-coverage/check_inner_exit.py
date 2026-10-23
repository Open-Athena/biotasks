"""Actual Bash/Git stages show whether an inner runner failure is swallowed.

Synthetic test output is deliberate; no biological case or original reward is
regraded. The exact source stage script runs in a private local Git fixture.
"""
from dataclasses import dataclass
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time
from check_completion import load

ROOT=Path(__file__).resolve().parent

@dataclass
class Result:
    stdout:str
    stderr:str
    exit_code:int
    def truncated(self,max_chars):return (self.stdout+'\n'+self.stderr)[-max_chars:]

class ActualShell:
    def __init__(self,root,code):self.root=root;self.code=code;self.calls=[]
    def exec(self,command,timeout):
        phase='FAILED' if not self.calls else 'PASSED'
        command=command.replace('/workspace',str(self.root))
        env={**os.environ,'FIXTURE_STATUS':phase,'FIXTURE_EXIT':str(self.code)}
        p=subprocess.run(['bash','-lc',command],env=env,capture_output=True,text=True,timeout=timeout,check=False)
        self.calls.append({'outer_exit':p.returncode,'requested_inner_exit':self.code,'end_marker_present':'R2E_END_TEST_OUTPUT' in p.stdout.splitlines()})
        return Result(p.stdout,p.stderr,p.returncode)


def main():
    original=load('inner_original',ROOT/'upstream/pipelines/pr_runtime_validate.py')
    candidate=load('inner_candidate',ROOT/'candidate/pr_runtime_validate.py')
    rows=[]
    with tempfile.TemporaryDirectory(prefix='biotasks32-inner-exit-') as temp:
        root=Path(temp)
        def git(*args):return subprocess.check_output(['git','-C',str(root),*args],text=True,stderr=subprocess.DEVNULL).strip()
        git('init','-q');git('config','user.email','fixture@example.invalid');git('config','user.name','Fixture')
        (root/'pytest_fixture.py').write_text("import os\nprint('tests/test_x.py::test_fix '+os.environ['FIXTURE_STATUS']+' [50%]')\nprint('tests/test_x.py::test_stable PASSED [100%]')\nraise SystemExit(int(os.environ['FIXTURE_EXIT']))\n")
        git('add','pytest_fixture.py');git('commit','-qm','fixture');ref=git('rev-parse','HEAD')
        for code in (0,1,2,124,137):
            pair={'inner_exit':code}
            for label,module in [('original',original),('outer_completion_candidate',candidate)]:
                sb=ActualShell(root,code)
                result=module.validate_pr(sandbox=sb,base_commit=ref,patch='',test_patch='',test_cmds=['python3 pytest_fixture.py'],language='python')
                pair[label]={'status':result.status,'reason':result.reason,'f2p':result.fail_to_pass,'p2p':result.pass_to_pass,'calls':sb.calls}
                assert result.status=='verified' and len(result.fail_to_pass)==1 and len(result.pass_to_pass)==1
                assert all(c['outer_exit']==0 and c['end_marker_present'] for c in sb.calls)
            rows.append(pair)
    assert not root.exists()
    report={'scope':'Actual Bash/Git execution with synthetic runner output through original/candidate validator; not biological task validation','cases':rows,'temporary_directory_removed':True,
            'finding':'Outer exit and marker presence do not enforce inner test-command completion; test exit 2, 124 and 137 are swallowed and accepted on parseable partial lines','model_calls':0,'remote_jobs':0}
    (ROOT/'inner-exit-results.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'cases':len(rows),'unsafe_inner_exit_codes_accepted':[2,124,137],'temporary_directory_removed':True}))

if __name__=='__main__':main()
