import importlib.util,json,types,sys,time,resource
from pathlib import Path
root=Path(__file__).resolve().parent
sys.path.insert(0,str(root))
from verify_export import baseline_assertion_gate, controls_passed, pytest_statuses
spec=importlib.util.spec_from_file_location('v',sys.argv[1]);v=importlib.util.module_from_spec(spec);spec.loader.exec_module(v)
f='tests/test_example.py::test_fix';p='tests/test_example.py::test_existing'
log=f+' FAILED\n'+p+' PASSED\nE       AssertionError: wrong answer\n'
records=[]
for name,text,expected in [('assertion',log,True),('application_error_logging',log+'ERROR nipype.workflow:tools.py:46 Node failed\n',True),('collection_error',log+'ERROR collecting tests/test_other.py\n',False),('real_test_error',log+'tests/test_other.py::test_bad ERROR\n',False),('missing_assertion',f+' FAILED\n'+p+' PASSED\n',False)]:
 result=baseline_assertion_gate(types.SimpleNamespace(pre_log=text,fail_to_pass=[f],pass_to_pass=[p]),v.parse_logs);assert result==expected,(name,result);records.append({'name':name,'expected':expected,'actual':result})
for name,reward,resolved,disposition,expected in [('partial_credit',0.5,False,'graded',True),('false_acceptance',1,True,'graded',False),('unresolved',0,False,'unresolved_patch_control',False)]:
 controls=[{'name':'reference','strict_reference_pass':True},{'name':'negative','disposition':disposition,'details':{'reward':reward,'resolved':resolved}}];result=controls_passed(controls,True);assert result==expected;records.append({'name':name,'expected':expected,'actual':result})
(root/'evidence/export-gate-regression-checks.json').write_text(json.dumps({'checks':records,'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss},indent=2)+'\n')
print('8 export-gate regression checks passed')
