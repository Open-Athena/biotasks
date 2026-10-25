"""Exercise build failure/source mutation/deadline before any test body.

Uses the explicit own-command prototype from compiled-proof, not a general
recorded-shell classifier or deployed runtime policy.
"""
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

from check_lifecycle import load_original

BASE=Path(__file__).resolve().parent


def main():
    load_original()  # Source digest verification, no repo imports.
    proof=json.loads((BASE/'compiled-proof.json').read_text())
    template=next(x for x in proof['routes'] if x['route']=='recorded_rebuild')['stages'][1]['script']
    old_workspace=str(BASE/'inputs-private/compiled-001/workspace')
    old_scratch=str(BASE/'inputs-private/compiled-001')
    root=BASE/'inputs-private/build-failures-001'; root.mkdir(exist_ok=False)
    rows=[]
    try:
        for case,build in [
            ('failed_command',"raise SystemExit(7)\n"),
            ('mutating_command',"from pathlib import Path\nPath('value.h').write_text('#define ANSWER 42\\n')\n"),
            ('deadline',"import time\ntime.sleep(20)\n"),
        ]:
            scratch=root/case; repo=scratch/'workspace';repo.mkdir(parents=True)
            env=dict(os.environ,GIT_CONFIG_GLOBAL=str(scratch/'git-global'),GIT_CONFIG_NOSYSTEM='1',PYTHONDONTWRITEBYTECODE='1')
            (repo/'build.py').write_text(build);(repo/'value.h').write_text('#define ANSWER 0\n')
            def git(*args):
                return subprocess.check_output(['git',*args],cwd=repo,env=env,text=True,stderr=subprocess.DEVNULL,timeout=10)
            git('init','-q');git('add','.');git('-c','user.name=fixture','-c','user.email=fixture@example.invalid','commit','-qm','Build behavior fixture')
            base=git('rev-parse','HEAD').strip()
            script=template.replace(old_workspace,str(repo)).replace(old_scratch,str(scratch))
            script=re.sub(r'git reset --hard [a-f0-9]{40}', 'git reset --hard '+base,script,count=1)
            # Keep the post-source patch exactly as in the compiled prototype.
            started=time.monotonic()
            # timeout's process group is used to stop bash and its build child.
            out=subprocess.run(['timeout','--signal=TERM','--kill-after=1','0.5' if case=='deadline' else '10','bash','-c',script],cwd=repo,env=env,text=True,capture_output=True,timeout=12,check=False)
            expected={'failed_command':78,'mutating_command':79,'deadline':124}[case]
            assert out.returncode==expected,(case,out.returncode,out.stdout,out.stderr)
            assert 'R2E_START_TEST_OUTPUT' not in out.stdout
            assert not (repo/'test-ran').exists()
            rows.append(dict(case=case,script=script,exit=out.returncode,stdout=out.stdout,stderr=out.stderr,seconds=time.monotonic()-started,test_output_marker_emitted=False,build_command_completed=case!='deadline',tests_executed=False))
    finally:
        shutil.rmtree(root)
    result=dict(synthetic=True,cases=rows,scratch_removed=not root.exists(),native_or_model_jobs=0,runtime_integrated=False,scope='Explicit own recorded-command mechanism only. Does not classify arbitrary shell, prove import provenance, or alter native deadlines. Local 0.5s deadline is a fixture, not a native timeout change.')
    (BASE/'build-failure-proof.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='cases'},indent=2))

if __name__=='__main__':main()
