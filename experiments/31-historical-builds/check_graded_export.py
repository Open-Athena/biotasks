"""Execute candidate emitted scripts plus exact graded verifier on compiled unittest fixture."""
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import tempfile

from check_compiled_lifecycle import load_functions

ROOT = Path(__file__).resolve().parent
VERIFIER_SHA = '154ce5cbff54463ad7c08756abd22d198e17bd7ae3ff6ccdf994f5bf16ad021b'


def main():
    verifier = ROOT/'upstream/pipelines/_pr_runtime_verifier.py'
    assert hashlib.sha256(verifier.read_bytes()).hexdigest() == VERIFIER_SHA
    helper = {'shlex':shlex}
    load_functions(ROOT/'candidate/pipelines/runtime_rebuild.py',['rebuild_script', 'reset_test_script'],helper)
    ns = {'_DIFF_HEADER_RE':re.compile(r'^diff --git a/(.+) b/(.+)$',re.MULTILINE),'rebuild_script':helper['rebuild_script'],'reset_test_script':helper['reset_test_script']}
    load_functions(ROOT/'candidate/pipelines/pr_runtime.py',['_path_prelude_for_language','_files_in_patch','build_eval_script'],ns)
    results=[]
    with tempfile.TemporaryDirectory(prefix='biotasks31-graded-') as td:
        root=Path(td)
        repo=root/'workspace';repo.mkdir()
        tests=root/'tests';tests.mkdir()
        logs=root/'logs/verifier';logs.mkdir(parents=True)
        env={**os.environ,'HOME':str(root),'GIT_CONFIG_NOSYSTEM':'1','GIT_CONFIG_GLOBAL':str(root/'gitconfig')}
        def run(args, **kw):
            return subprocess.run(args,cwd=repo,env=env,text=True,capture_output=True,timeout=10,**kw)
        def git(*args):
            return run(['git',*args],check=True).stdout.strip()
        git('init','-q');git('config','user.name','Synthetic fixture');git('config','user.email','fixture@example.invalid')
        (repo/'value.c').write_text('int fixture_value(void) { return 1; }\n')
        (repo/'test_value.py').write_text('import ctypes, unittest\nclass ValueTests(unittest.TestCase):\n def test_fixed(self):\n  self.assertEqual(ctypes.CDLL("./fixture.so").fixture_value(),2)\n def test_stable(self):\n  self.assertGreaterEqual(ctypes.CDLL("./fixture.so").fixture_value(),1)\n')
        git('add','.');git('commit','-qm','Base fixture')
        base=git('rev-parse','HEAD')
        f2p=['test_value.ValueTests.test_fixed'];p2p=['test_value.ValueTests.test_stable']
        (tests/'f2p.json').write_text(json.dumps(f2p));(tests/'p2p.json').write_text(json.dumps(p2p))
        shutil.copyfile(verifier,tests/'verifier.py')
        for side in ['nop','oracle','build_failure','untracked_command_failure','invalid_base','new_test','reset_obstructed']:
            git('reset','--hard',base);git('clean','-fdx')
            if side!='nop': (repo/'value.c').write_text('int fixture_value(void) { return 2; }\n')
            # A previous successful reward must not survive a failed rebuild.
            (logs/'reward.txt').write_text('1.0\n')
            (logs/'reward-details.json').write_text('{"resolved":true}')
            cmd='python3 -m unittest -v test_value'
            if side=='untracked_command_failure': cmd+=' && false'
            rebuild=['false\necho MASKED_FAILURE'] if side=='build_failure' else ['cc -shared -fPIC -O0 value.c -o fixture.so']
            patch = ''
            if side in ('new_test','reset_obstructed'):
                patch = 'diff --git a/new_test.txt b/new_test.txt\nnew file mode 100644\n--- /dev/null\n+++ b/new_test.txt\n@@ -0,0 +1 @@\n+expected test payload\n'
                if side == 'new_test': (repo/'new_test.txt').write_text('tampered old content\n')
                else: (repo/'new_test.txt').mkdir()
            selected_base = '0000000000000000000000000000000000000000' if side == 'invalid_base' else base
            script=ns['build_eval_script'](selected_base,patch,[cmd],fail_to_pass=f2p,pass_to_pass=p2p,rebuild_cmds=rebuild)
            script=script.replace('/workspace',str(repo)).replace('/logs/verifier',str(logs))
            path=tests/'test.sh';path.write_text(script)
            r=run(['bash',str(path)])
            reward=float((logs/'reward.txt').read_text())
            details=json.loads((logs/'reward-details.json').read_text())
            if side in ('invalid_base','reset_obstructed'):
                assert r.returncode!=0 and reward==0 and details['parse_status']=='setup_incomplete'
            elif side=='build_failure':
                assert reward==0 and details['resolved'] is False and details['parse_status']=='rebuild_incomplete'
                assert r.returncode!=0 and 'MASKED_FAILURE' not in r.stdout
            else:
                assert details['parse_status']=='ok' and details['tests_parsed']==2
                assert details['f2p_total']==1 and details['p2p_total']==1
                assert reward==(0 if side=='nop' else 1)
                assert details['resolved']==(side!='nop')
                assert details['command_resolved']==(side in ('oracle','new_test'))
                if side=='new_test': assert (repo/'new_test.txt').read_text()=='expected test payload\n'
            results.append({'case':side,'script_exit':r.returncode,'reward':reward,'details':details})
    report={'scope':'Actual unittest execution on synthetic compiled library through candidate exported shell and unchanged pinned graded verifier; local paths, no Harbor/Docker/biological repo','verifier_sha256':VERIFIER_SHA,'cases':results,'all_assertions_passed':True,'temporary_directory_removed':not root.exists(),'limits':['No full generation CLI or Docker/Harbor execution','Does not establish MACS task recovery','No timeouts or process cancellation measured here']}
    (ROOT/'graded-export-results.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'cases':len(results),'all_assertions_passed':True,'temporary_directory_removed':not root.exists()}))


if __name__=='__main__': main()
