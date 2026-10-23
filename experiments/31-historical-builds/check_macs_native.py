"""No-Docker checks for frozen scripts and orchestration timeout guards."""
import json
from pathlib import Path
import shutil
import time
from types import SimpleNamespace
import macs_native as driver

executor,parsers,original,candidate=driver.load()
manifest=driver.verify(original,candidate)
root=Path(__file__).resolve().parent/'inputs-private/native-guard-fixture'
assert not root.exists();root.mkdir()
class Sandbox:
    def __init__(self,code):self.code=code;self.calls=0
    def exec(self,command,*,timeout):
        self.calls+=1
        return SimpleNamespace(exit_code=self.code,duration_sec=0.01,stdout='fixture',stderr='')
checks=[]
try:
    for name,code,remaining,expected,calls in [('ordinary_failure',1,100,None,1),('client_timeout',124,100,driver.ArmTimeout,1),('insufficient_allowance',0,1,driver.ArmTimeout,0)]:
        out=root/name;out.mkdir();sandbox=Sandbox(code)
        recorder=driver.Recorder(sandbox,out,{},time.monotonic()+remaining)
        try:
            result=recorder.exec('fixture',timeout=10)
            assert expected is None and result.exit_code==code
        except driver.ArmTimeout:
            assert expected is driver.ArmTimeout
        assert sandbox.calls==calls
        checks.append(name)
    sandbox=Sandbox(0);recorder=driver.Recorder(sandbox,root,{},time.monotonic()+100)
    try:recorder.exec('echo R2E_START_TEST_OUTPUT; changed',timeout=10)
    except AssertionError:pass
    else:raise AssertionError('Changed stage accepted')
    assert sandbox.calls==0;checks.append('changed_stage_rejected_before_execution')
finally:shutil.rmtree(root)
report={'frozen_scripts_verified':4,'default_off_parity':True,'guard_checks':checks,'fixture_removed':not root.exists(),'docker_execution':False,'model_calls':0}
print(json.dumps(report))
