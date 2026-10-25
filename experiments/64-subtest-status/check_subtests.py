"""Own unittest fixtures through real pytest and exact original parsers/verifiers."""
import importlib.metadata
import hashlib
import io
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

BASE=Path(__file__).resolve().parent
SOURCE=BASE.parents[2]/'48/experiments/48-generation-manifest/inputs-private/installed-proof-004/source-cache/source'
TEMPLATE='''import unittest
CASE = {case!r}
class Cases(unittest.TestCase):
    def test_parameters(self):
        values = ['plain', 'second'] if CASE != 'awkward' else ['space value', 'FAILED) ][ odd', 'space value']
        for index, value in enumerate(values):
            with self.subTest(label=value, index=index):
                if CASE in ('failure','awkward') and index == 0:
                    self.fail('own intentional subtest failure')
                if CASE == 'error' and index == 0:
                    raise ValueError('own intentional subtest error')
                if CASE == 'skip' and index == 0:
                    self.skipTest('own intentional skip')
                self.assertTrue(True)
    def test_stable(self):
        self.assertEqual(1, 1)
    def test_plain(self):
        self.assertNotEqual(CASE, 'ordinary_failure')
'''
ORACLE='''import unittest,json,io,test_subtests
class Recording(unittest.TextTestResult):
 def __init__(self,*a,**kw):
  super().__init__(*a,**kw);self.subtests=[]
 def addSubTest(self,test,subtest,error):
  self.subtests.append({'parent':test.id(),'subtest':str(subtest),'status':'PASSED' if error is None else 'FAILED' if issubclass(error[0],test.failureException) else 'ERROR'})
  super().addSubTest(test,subtest,error)
result=unittest.TextTestRunner(stream=io.StringIO(),verbosity=2,resultclass=Recording).run(unittest.defaultTestLoader.loadTestsFromModule(test_subtests))
print(json.dumps({'successful':result.wasSuccessful(),'tests':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'skips':len(result.skipped),'subtests':result.subtests}))
'''

def execute(args,cwd,env):
    r=subprocess.run(args,cwd=cwd,env=env,capture_output=True,text=True,timeout=15,check=False)
    return {'command':args,'exit':r.returncode,'stdout':r.stdout,'stderr':r.stderr}


def main():
    sources={}
    binding=json.loads((BASE/"source-binding.json").read_text())
    for name, digest in binding.items():
        assert hashlib.sha256((SOURCE/name).read_bytes()).hexdigest()==digest
    current=json.loads((BASE/"upstream-current-review.json").read_text())
    for item in current["files"]:
        path=BASE/"inputs-private/current-upstream"/item["path"]
        assert hashlib.sha256(path.read_bytes()).hexdigest()==item["sha256"]
    for label,path in [('native',SOURCE/'src/repo2rlenv/log_parsers/pytest_parser.py'),('standalone',SOURCE/'src/repo2rlenv/pipelines/_pr_runtime_verifier.py'),('current',BASE/'inputs-private/current-upstream/src/repo2rlenv/pipelines/_pr_runtime_verifier.py')]:
        ns={'__name__':'isolated_'+label};exec(compile(path.read_text(),str(path),'exec'),ns);sources[label]=(path,ns)
    scratch=BASE/'inputs-private/fixture-002';scratch.mkdir(exist_ok=False)
    report=[]
    try:
        for case in ['passing','failure','error','skip','ordinary_failure','awkward']:
            folder=scratch/case;folder.mkdir();(folder/'test_subtests.py').write_text(TEMPLATE.format(case=case))
            env=dict(os.environ,PYTEST_DISABLE_PLUGIN_AUTOLOAD='1',PYTHONDONTWRITEBYTECODE='1')
            real=execute([sys.executable,'-B','-m','pytest','-v','--color=no','-p','no:cacheprovider','test_subtests.py'],folder,env)
            oracle_run=execute([sys.executable,'-B','-c',ORACLE],folder,env);assert oracle_run['exit']==0, oracle_run
            oracle=json.loads(oracle_run['stdout']);assert oracle['tests']==3
            assert (real['exit']==0)==oracle['successful']
            parent='test_subtests.py::Cases::test_parameters';stable='test_subtests.py::Cases::test_stable';plain='test_subtests.py::Cases::test_plain'
            maps={name:ns['parse_pytest'](real['stdout']) for name,(path,ns) in sources.items()}
            assert all(v==maps['native'] for v in maps.values())
            grades={name:ns['grade']([parent],[stable,plain],maps[name],runner='pytest') for name,(path,ns) in sources.items() if name!='native'}
            if case in ['failure','error','awkward']:
                assert maps['native'][parent]=='PASSED' and not oracle['successful']
                assert any(s['status'] in ['FAILED','ERROR'] for s in oracle['subtests'])
                assert all(g['reward']==1 and g['resolved'] for g in grades.values())
            elif case=='ordinary_failure':
                assert maps['native'][plain]=='FAILED' and all(not g['resolved'] for g in grades.values())
            else:assert oracle['successful'] and real['exit']==0
            report.append(dict(case=case,pytest=real,stdlib_oracle=oracle,native_and_standalone_statuses=maps,toy_declared_f2p=[parent],toy_declared_p2p=[stable,plain],tracked_grade_probe=grades,subfailed_lines=[s for s in real['stdout'].splitlines() if s.startswith('SUBFAILED')]))
    finally:shutil.rmtree(scratch)
    result=dict(synthetic=True,observed_biological_inputs=False,python=sys.version,pytest=importlib.metadata.version('pytest'),actual_pytest_processes=6,actual_stdlib_oracle_processes=6,parsers_changed=False,fixtures=report,scratch_removed=not scratch.exists(),native_or_model_calls=0,scientific_acceptance=False,limits='Own fixture grading probe declares toy tracked identities; it is not an exported biological task or native rerun. Original command exit remains nonzero on failed subtests; strict clean-command acceptance is not bypassed. No parser candidate deployed.')
    (BASE/'fixture-proof.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='fixtures'},indent=2))

if __name__=='__main__':main()
