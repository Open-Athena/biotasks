"""Bounded compiled fixture through pinned native/export script builders.

The opt-in rebuild adapter here is a mechanism experiment, not an integrated
pipeline patch. Only absolute sandbox paths are remapped for local execution.
"""
import ast
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parent


def load_functions(path, names, namespace):
    tree = ast.parse(path.read_text())
    nodes = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in names]
    assert {n.name for n in nodes} == set(names)
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(path), 'exec'), namespace)


def rebuild_guard(commands, exported=False):
    # A separate bash process is deliberate: `(... set -e ...) || ...` would
    # suppress errexit throughout the subshell and can mask a failed build.
    command = '\n'.join(commands)
    guard = f'bash -euo pipefail -c {shlex.quote(command)}\nR2E_REBUILD_RC=$?\n'
    guard += 'if [ "$R2E_REBUILD_RC" -ne 0 ]; then\n'
    if exported:
        guard += '  echo 0.0 > /logs/verifier/reward.txt\n'
        guard += '  echo \'{"parse_status":"rebuild_failed"}\' > /logs/verifier/reward-details.json\n'
    guard += '  echo R2E_REBUILD_FAILED >&2\n  exit "$R2E_REBUILD_RC"\nfi\n'
    return guard


def adapt(script, commands, exported=False):
    anchor = '( python3 check.py ) > /logs/verifier/test_output.log 2>&1' if exported else 'echo R2E_START_TEST_OUTPUT'
    assert script.count(anchor) == 1
    return script.replace(anchor, rebuild_guard(commands, exported) + anchor)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--candidate', action='store_true')
    args = parser.parse_args()
    provenance = json.loads((ROOT / 'provenance.json').read_text())
    for entry in provenance['files']:
        assert hashlib.sha256((ROOT / entry['path']).read_bytes()).hexdigest() == entry['sha256']
    native = {'_HEREDOC': 'EOF_R2E_VALIDATE'}
    exported = {'_DIFF_HEADER_RE': re.compile(r'^diff --git a/(.+) b/(.+)$', re.MULTILINE)}
    load_functions(ROOT / 'upstream/pipelines/pr_runtime_validate.py', ['_heredoc_apply', '_build_stage_script'], native)
    load_functions(ROOT / 'upstream/pipelines/pr_runtime.py', ['_path_prelude_for_language', '_files_in_patch', 'build_eval_script'], exported)
    candidate_native = dict(native)
    candidate_export = dict(exported)
    helper = {'shlex': shlex}
    if args.candidate:
        load_functions(ROOT / 'candidate/pipelines/runtime_rebuild.py', ['rebuild_script', 'reset_test_script'], helper)
        candidate_native['rebuild_script'] = helper['rebuild_script']
        candidate_export['rebuild_script'] = helper['rebuild_script']
        candidate_export['reset_test_script'] = helper['reset_test_script']
        load_functions(ROOT / 'candidate/pipelines/pr_runtime_validate.py', ['_build_stage_script'], candidate_native)
        load_functions(ROOT / 'candidate/pipelines/pr_runtime.py', ['build_eval_script'], candidate_export)
        # Default-off must retain the exact original generated script.
        assert native['_build_stage_script']('base', apply_patch=None, apply_test_patch=None, test_cmds=['true']) == candidate_native['_build_stage_script']('base', apply_patch=None, apply_test_patch=None, test_cmds=['true'])
        assert exported['build_eval_script']('base', '', ['true']) == candidate_export['build_eval_script']('base', '', ['true'])
    results = []
    with tempfile.TemporaryDirectory(prefix='biotasks31-compiled-') as temp:
        root = Path(temp)
        repo = root / 'workspace'
        repo.mkdir()
        env = {**os.environ, 'HOME': str(root), 'GIT_CONFIG_NOSYSTEM': '1', 'GIT_CONFIG_GLOBAL': str(root/'gitconfig')}
        def run(args, **kwargs):
            return subprocess.run(args, cwd=repo, env=env, capture_output=True, text=True, timeout=10, **kwargs)
        def git(*args):
            return run(['git', *args], check=True).stdout.strip()
        git('init', '-q')
        git('config', 'user.email', 'fixture@example.invalid')
        git('config', 'user.name', 'Synthetic fixture')
        (repo/'value.c').write_text('int fixture_value(void) { return 1; }\n')
        (repo/'check.py').write_text('import ctypes, pathlib, hashlib\np=pathlib.Path("fixture.so").resolve()\nlib=ctypes.CDLL(str(p))\nv=lib.fixture_value()\nprint("IMPORT",p,"VALUE",v,"SHA256",hashlib.sha256(p.read_bytes()).hexdigest(),flush=True)\nassert v == 2\nprint("FIXTURE_PASS",flush=True)\n')
        git('add', '.')
        git('commit', '-qm', 'Base revision')
        base = git('rev-parse', 'HEAD')
        (repo/'value.c').write_text('int fixture_value(void) { return 2; }\n')
        patch = git('diff') + '\n'
        build = 'cc -shared -fPIC -O0 value.c -o fixture.so'
        for kind in ['native', 'export']:
            for mode in (['baseline', 'rebuild'] if kind == 'native' else ['baseline', 'rebuild', 'preserve_stale']):
                for side in ['nop', 'oracle']:
                    git('reset', '--hard', base)
                    git('clean', '-fdx')
                    # Each arm begins with a bootstrap binary from the fixed ref.
                    (repo/'value.c').write_text('int fixture_value(void) { return 2; }\n')
                    run(['bash', '-c', build], check=True)
                    bootstrap_bytes = (repo/'fixture.so').read_bytes()
                    bootstrap_sha = hashlib.sha256(bootstrap_bytes).hexdigest()
                    if kind == 'native':
                        script = native['_build_stage_script'](base, apply_patch=patch if side=='oracle' else None, apply_test_patch=None, test_cmds=['python3 check.py'])
                    else:
                        # Reproduce exported image's reset/clean; oracle/source
                        # edits occur later, as they do before exported test.sh.
                        git('reset', '--hard', base)
                        git('clean', '-fdx')
                        if side=='oracle':
                            run(['git','apply','-'],input=patch,check=True)
                        if mode == 'preserve_stale':
                            # Explicit negative control for the tempting workaround
                            # of retaining fixed-ref compiled bytes after reset.
                            (repo/'fixture.so').write_bytes(bootstrap_bytes)
                        script = exported['build_eval_script'](base, '', ['python3 check.py'])
                    if mode == 'rebuild':
                        if args.candidate:
                            script = candidate_native['_build_stage_script'](base, apply_patch=patch if side=='oracle' else None, apply_test_patch=None, test_cmds=['python3 check.py'], rebuild_cmds=[build]) if kind=='native' else candidate_export['build_eval_script'](base, '', ['python3 check.py'], rebuild_cmds=[build])
                        else:
                            script = adapt(script, [build], kind=='export')
                    logs = root/'logs'/'verifier'
                    logs.mkdir(parents=True, exist_ok=True)
                    for f in logs.iterdir():
                        f.unlink()
                    script = script.replace('/workspace',str(repo)).replace('/logs/verifier',str(logs))
                    r = run(['bash','-c',script])
                    combined = r.stdout+r.stderr
                    imported = 'IMPORT ' in r.stdout
                    passed = 'FIXTURE_PASS' in r.stdout
                    expected_import = mode in ('rebuild', 'preserve_stale')
                    expected_pass = mode == 'preserve_stale' or (mode == 'rebuild' and side == 'oracle')
                    assert imported == expected_import and passed == expected_pass, (kind,mode,side,combined)
                    binary = repo/'fixture.so'
                    if mode=='rebuild':
                        assert ('VALUE 1 ' if side=='nop' else 'VALUE 2 ') in r.stdout
                        assert (hashlib.sha256(binary.read_bytes()).hexdigest()==bootstrap_sha) == (side=='oracle')
                    results.append({'kind':kind,'mode':mode,'side':side,'script_exit':r.returncode,'import_succeeded':imported,'test_passed':passed,'stale_false_positive':mode=='preserve_stale' and side=='nop','binary_sha256':hashlib.sha256(binary.read_bytes()).hexdigest() if binary.exists() else None,'output':r.stdout.replace(str(root),'<fixture>'),'reward':(logs/'reward.txt').read_text().strip() if (logs/'reward.txt').exists() else None})
            # Multiline build failure must not reach tests or be hidden by a
            # following successful command. Exercise both builder outputs.
            git('reset','--hard',base)
            git('clean','-fdx')
            script = native['_build_stage_script'](base,apply_patch=None,apply_test_patch=None,test_cmds=['python3 check.py']) if kind=='native' else exported['build_eval_script'](base,'',['python3 check.py'])
            if args.candidate:
                cmds = ['false\nprintf SHOULD_NOT_RUN']
                script = candidate_native['_build_stage_script'](base, apply_patch=None, apply_test_patch=None, test_cmds=['python3 check.py'], rebuild_cmds=cmds) if kind=='native' else candidate_export['build_eval_script'](base, '', ['python3 check.py'], rebuild_cmds=cmds)
            else:
                script = adapt(script,['false\nprintf SHOULD_NOT_RUN'],kind=='export')
            script = script.replace('/workspace',str(repo)).replace('/logs/verifier',str(logs))
            r = run(['bash','-c',script])
            assert r.returncode != 0
            if not args.candidate or kind=='export':
                assert 'R2E_REBUILD_FAILED' in r.stderr
            assert 'SHOULD_NOT_RUN' not in r.stdout and 'IMPORT ' not in r.stdout
            assert 'R2E_START_TEST_OUTPUT' not in r.stdout
            results.append({'kind':kind,'mode':'failed_rebuild','script_exit':r.returncode,'tests_started':False,'failure_guard':True})
        compiler = run(['cc','--version'],check=True).stdout.splitlines()[0]
    report={'scope':'Synthetic C shared library; pinned native/export shell builders, local path mapping and optional research rebuild adapter. No Docker, model, biological PR, full pipeline or Harbor execution.','compiler':compiler,'cases':results,'case_count':len(results),'all_assertions_passed':True,'temporary_directory_removed':not root.exists(),'limits':['Export uses upstream binary reward fallback, not graded parser','Fixture has no dependency installation or historical dependency drift','Adapter is not wired through pipeline configuration/export metadata','No MACS recovery claim']}
    report['implementation'] = 'candidate builders' if args.candidate else 'research script adapter'
    (ROOT/('candidate-lifecycle-results.json' if args.candidate else 'compiled-lifecycle-results.json')).write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'cases':len(results),'all_assertions_passed':True,'temporary_directory_removed':not root.exists()}))


if __name__ == '__main__':
    main()
