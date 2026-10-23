"""Run only pinned OpenMS acquisition, with one declared checkout allowance."""
import ast
import hashlib
import json
import logging
import os
from pathlib import Path
import re
import shutil
import subprocess
import threading
import time
from types import SimpleNamespace
from collections.abc import Callable

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'evidence';OUT.mkdir(exist_ok=True)
REF='5edf83948816aee51225949dd0e613bd40f69c47'
SECONDS=int(os.environ['CHECKOUT_SECONDS']);assert SECONDS in (60,300)
REPORT={'repo':'OpenMS/OpenMS','ref':REF,'checkout_seconds':SECONDS,'model_calls':0,'bootstrap_started':False,'started':time.time(),'calls':[]}


def run(args,**kwargs):
    number=len(REPORT['calls'])+1
    row={'args':args,'timeout_seconds':kwargs.get('timeout'),'started':time.time()}
    REPORT['calls'].append(row)
    try:
        result=subprocess.run(args,**kwargs)
        row['exit_code']=result.returncode
        for name in ('stdout','stderr'):
            data=getattr(result,name) or ''
            if isinstance(data,str):data=data.encode()
            (OUT/f'git-{number:02d}-{name}.txt').write_bytes(data)
            row[name+'_sha256']=hashlib.sha256(data).hexdigest()
        return result
    except subprocess.TimeoutExpired as error:
        row['timeout']=True
        for name,attr in [('stdout','output'),('stderr','stderr')]:
            data=getattr(error,attr) or b''
            if isinstance(data,str):data=data.encode()
            (OUT/f'git-{number:02d}-{name}.txt').write_bytes(data)
            row[name+'_sha256']=hashlib.sha256(data).hexdigest()
        raise
    finally:
        row['finished']=time.time()
        (OUT/'progress.json').write_text(json.dumps(REPORT,indent=2)+'\n')


def definitions(path,names,namespace):
    tree=ast.parse(path.read_text())
    nodes=[n for n in tree.body if isinstance(n,(ast.ClassDef,ast.FunctionDef)) and n.name in names]
    assert {n.name for n in nodes}==set(names)
    module=ast.Module(body=[ast.ImportFrom(module='__future__',names=[ast.alias(name='annotations')],level=0),*nodes],type_ignores=[])
    exec(compile(ast.fix_missing_locations(module),str(path),'exec'),namespace)


def main():
    pins=json.loads((ROOT/'source-pins.json').read_text())
    for name,expected in pins.items():assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==expected
    source='runner-original.py' if SECONDS==60 else 'runner-candidate.py'
    REPORT['runner_sha256']=pins[source]
    ns=dict(globals(),subprocess=SimpleNamespace(run=run),logger=logging.getLogger('checkout-only'))
    definitions(ROOT/'auth.py',{'auth_clone_url'},ns)
    definitions(ROOT/source,{'BootstrapError','_scrub_token','_run_git_streaming','_shallow_clone_at_ref','_resolve_head_sha'},ns)
    REPORT['git_version']=subprocess.check_output(['git','--version'],text=True,timeout=10).strip()
    dest=ROOT/'checkout';assert not dest.exists()
    try:
        options={} if SECONDS==60 else {'checkout_timeout':SECONDS}
        ns['_shallow_clone_at_ref']('https://github.com/OpenMS/OpenMS.git',REF,None,dest,**options)
        actual=ns['_resolve_head_sha'](dest)
        assert actual==REF
        REPORT['checked_out_ref']=actual
        REPORT['tracked_status']=subprocess.check_output(['git','-C',str(dest),'status','--porcelain','--untracked-files=no'],text=True,timeout=60)
        REPORT['tree']=subprocess.check_output(['git','-C',str(dest),'rev-parse','HEAD^{tree}'],text=True,timeout=30).strip()
        REPORT['checkout_completed']=True
    except Exception as error:
        REPORT['error_type']=type(error).__name__
        REPORT['error']=str(error)[:500]
        REPORT['checkout_completed']=False
    finally:
        # The supervisor removes this whole container before another arm starts;
        # a timed-out git can leave descendants, so do not continue in it.
        REPORT['finished']=time.time()
        (OUT/'checkout-result.json').write_text(json.dumps(REPORT,indent=2)+'\n')
        print(json.dumps(REPORT),flush=True)

if __name__=='__main__':main()
