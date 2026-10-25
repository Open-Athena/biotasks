"""Real compiled fixture; pinned native stage/parser, owned-path substitutions only.

Mechanism evidence, not a generic replay policy or native biology acceptance.
"""
import ast
import hashlib
import json
import os
import shlex
import shutil
import subprocess
import sys
import time
from pathlib import Path

BASE = Path(__file__).resolve().parent
SOURCE = BASE.parents[2] / '48/experiments/48-generation-manifest/inputs-private/installed-proof-004/source-cache/source'


def load_original():
    source = SOURCE / 'src/repo2rlenv/pipelines/pr_runtime_validate.py'
    parser = SOURCE / 'src/repo2rlenv/log_parsers/pytest_parser.py'
    binding = json.loads((BASE / 'source-binding.json').read_text())
    for path in [source, parser]:
        assert hashlib.sha256(path.read_bytes()).hexdigest() == binding[str(path.relative_to(SOURCE))]
    tree = ast.parse(source.read_text())
    wanted = {'_HEREDOC', '_heredoc_apply', '_build_stage_script', '_slice_test_output'}
    nodes = [n for n in tree.body if
             (isinstance(n, ast.FunctionDef) and n.name in wanted) or
             (isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id in wanted for t in n.targets))]
    ns = {}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(source), 'exec'), ns)
    pn = {}
    exec(compile(parser.read_text(), str(parser), 'exec'), pn)
    return ns, pn['parse_pytest']


def main():
    original, parse = load_original()
    scratch = BASE / 'inputs-private/compiled-001'
    scratch.mkdir(exist_ok=False)
    repo = scratch / 'workspace'
    repo.mkdir()
    env = dict(os.environ, GIT_CONFIG_GLOBAL=str(scratch/'git-global'),
               GIT_CONFIG_NOSYSTEM='1', PYTEST_DISABLE_PLUGIN_AUTOLOAD='1',
               PYTHONDONTWRITEBYTECODE='1', PYTHONPATH=str(repo))
    def command(args):
        return subprocess.run(args, cwd=repo, env=env, text=True,
                              capture_output=True, check=True, timeout=30).stdout
    reports = []
    try:
        shutil.copytree(BASE/'fixture', repo, dirs_exist_ok=True)
        (repo/'.gitignore').write_text('*.so\n')
        (repo/'value.h').write_text('#define ANSWER 0\n')
        command(['git','init','-q'])
        command(['git','add','.'])
        command(['git','-c','user.name=BioTasks fixture','-c','user.email=fixture@example.invalid','commit','-qm','Base fixture'])
        base = command(['git','rev-parse','HEAD']).strip()
        (repo/'value.h').write_text('#define ANSWER 1\n')
        patch = command(['git','diff','--','value.h'])
        command(['git','checkout','--','value.h'])
        python = shlex.quote(sys.executable)
        build_command = python + ' -B build.py'
        test_command = python + ' -B -m pytest -v -p no:cacheprovider test_regression.py'
        for route in ['original_cleanup','preserve_base_binary','preserve_head_binary','recorded_rebuild']:
            command(['git','reset','--hard',base])
            command(['git','clean','-fdx'])
            if route == 'preserve_head_binary':
                (repo/'value.h').write_text('#define ANSWER 1\n')
            command([sys.executable,'-B','build.py'])
            rows = []
            for stage in ['pre','post']:
                script = original['_build_stage_script'](base, apply_patch=patch if stage=='post' else None,
                    apply_test_patch=None, test_cmds=[test_command])
                assert script.count('/workspace') == 2
                script = script.replace('/workspace', str(repo))
                if route.startswith('preserve_'):
                    script = script.replace('git clean -fdx ', "git clean -fdx -e '*.so' ", 1)
                elif route == 'recorded_rebuild':
                    assert script.count('echo R2E_START_TEST_OUTPUT') == 1
                    # Prototype using our own known command, not a general shell classifier.
                    guard = 'git diff --binary > ' + shlex.quote(str(scratch/'before.patch')) + '\n'
                    guard += '( '+build_command+' ) || exit 78\n'
                    guard += 'git diff --binary > ' + shlex.quote(str(scratch/'after.patch')) + '\n'
                    guard += 'cmp '+shlex.quote(str(scratch/'before.patch'))+' '+shlex.quote(str(scratch/'after.patch'))+' || exit 79\n'
                    script = script.replace('echo R2E_START_TEST_OUTPUT', guard+'echo R2E_START_TEST_OUTPUT', 1)
                started = time.monotonic()
                result = subprocess.run(['bash','-c',script], cwd=repo, env=env, text=True,
                                        capture_output=True, timeout=40, check=False)
                output = original['_slice_test_output'](result.stdout)
                parsed = parse(output)
                expected_source = '#define ANSWER '+('1' if stage=='post' else '0')+'\n'
                assert (repo/'value.h').read_text() == expected_source
                assert command(['git','rev-parse','HEAD']).strip() == base
                rows.append(dict(stage=stage,script=script,stdout=result.stdout,stderr=result.stderr,
                                 shell_exit=result.returncode,parsed=parsed,seconds=time.monotonic()-started,
                                 selected_source_sha256=hashlib.sha256((repo/'value.h').read_bytes()).hexdigest(),
                                 binary_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in repo.glob('*.so')}))
            a,b = [x['parsed'] for x in rows]
            f2p = sorted(k for k,v in a.items() if v=='FAILED' and b.get(k)=='PASSED')
            p2p = sorted(k for k,v in a.items() if v=='PASSED' and b.get(k)=='PASSED')
            if route == 'original_cleanup':
                assert all('ModuleNotFoundError' in x['stdout'] and 'collected 0 items / 1 error' in x['stdout'] for x in rows)
                assert not f2p and not p2p
            elif route == 'preserve_base_binary':
                assert a['test_regression.py::test_regression'] == b['test_regression.py::test_regression'] == 'FAILED'
                assert not f2p and len(p2p)==1
                assert rows[0]['binary_sha256']==rows[1]['binary_sha256']
            elif route == 'preserve_head_binary':
                assert a['test_regression.py::test_regression'] == b['test_regression.py::test_regression'] == 'PASSED'
                assert not f2p and len(p2p)==2
            else:
                assert f2p==['test_regression.py::test_regression'] and p2p==['test_regression.py::test_stable']
                assert rows[0]['binary_sha256'] != rows[1]['binary_sha256']
            reports.append(dict(route=route,stages=rows,fail_to_pass=f2p,pass_to_pass=p2p))
    finally:
        shutil.rmtree(scratch)
    proof=dict(synthetic=True,observed_biological_inputs=False,real_pytest_processes=8,
               source_revision='27d04ee8203cd5b2f20c3997d13836e5f5b64238',routes=reports,
               own_recorded_build_command=build_command,scratch_removed=not scratch.exists(),
               original_stage_changes='Owned workspace substitution only; global git config redirected to own scratch. Candidate variants explicitly recorded.',
               native_jobs_or_model_calls=0,scientific_acceptance=False,
               limits='Mechanism fixture only; not arbitrary command classification, installed runtime integration, Docker export/verifier parity or a biological task result.')
    (BASE/'compiled-proof.json').write_text(json.dumps(proof,indent=2)+'\n')
    print(json.dumps({k:v for k,v in proof.items() if k!='routes'},indent=2))

if __name__=='__main__':
    main()
