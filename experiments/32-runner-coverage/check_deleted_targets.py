"""General diff selection fixtures plus frozen real inputs; no biological execution."""
import ast
import hashlib
import json
from pathlib import Path
import re
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parent


def load(path):
    names = {'_files_in_patch', '_runnable_test_files_in_patch', '_go_packages_from_test_files',
             'targeted_test_cmds_for_pr', 'normalize_test_cmds_for_runtime'}
    tree = ast.parse(path.read_text())
    ns = {'re': re, '_DIFF_HEADER_RE': re.compile(r'^diff --git a/(.+) b/(.+)$', re.MULTILINE),
          '_PYTEST_TARGETABLE_EXT': ('.py',), '_JEST_TARGETABLE_EXT': ('.js', '.jsx', '.ts', '.tsx', '.mjs', '.cjs')}
    nodes = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in names]
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(path), 'exec'), ns)
    return ns


def block(path, metadata=''):
    return f'diff --git a/{path} b/{path}\n'+metadata


def main():
    original = load(ROOT/'upstream/pipelines/pr_runtime.py')
    candidate = load(ROOT/'candidate/pr_runtime_targeting.py')
    selector = candidate['_runnable_test_files_in_patch']
    samples = [
        ('modified', block('tests/test_a.py', '--- a/tests/test_a.py\n+++ b/tests/test_a.py\n@@ -1 +1 @@\n-a\n+b\n'), ['tests/test_a.py']),
        ('deleted', block('tests/test_a.py', 'deleted file mode 100644\n--- a/tests/test_a.py\n+++ /dev/null\n'), []),
        ('dev_null_only', block('tests/test_a.py', '--- a/tests/test_a.py\n+++ /dev/null\n'), []),
        ('empty_deleted', block('tests/test_a.py', 'deleted file mode 100644\n'), []),
        ('new', block('tests/test_a.py', 'new file mode 100644\n--- /dev/null\n+++ b/tests/test_a.py\n'), ['tests/test_a.py']),
        ('renamed', 'diff --git a/tests/old.py b/tests/new.py\nsimilarity index 100%\nrename from tests/old.py\nrename to tests/new.py\n', ['tests/new.py']),
        ('hunk_literal', block('tests/test_a.py', '@@ -1 +1 @@\n+++ /dev/null\n'), ['tests/test_a.py']),
        ('duplicate', block('tests/test_a.py')*2, ['tests/test_a.py']),
        ('empty', '', []),
        ('mixed', block('tests/test_old.py', 'deleted file mode 100644\n')+block('tests/test_new.py'), ['tests/test_new.py']),
    ]
    rows=[]
    for name, diff, expected in samples:
        actual=selector(diff)
        assert actual==expected, name
        assert candidate['_files_in_patch'](diff)==original['_files_in_patch'](diff)
        rows.append({'case':name,'expected':expected,'actual':actual})
    runner_rows=[]
    for command, gone, keep, expected in [
        ('python -m pytest -v','tests/test_old.py','tests/test_new.py','python -m pytest -v tests/test_new.py'),
        ('npx jest','tests/old.test.js','tests/new.test.js','npx jest tests/new.test.js'),
        ('go test -v ./...','old/old_test.go','new/new_test.go','go test -v ./new'),
        ('python -m pytest -v tests/','tests/test_old.py','tests/test_new.py','python -m pytest -v tests/'),
    ]:
        paths=selector(block(gone,'deleted file mode 100644\n')+block(keep))
        actual=candidate['targeted_test_cmds_for_pr']([command],paths)
        assert actual==[expected]
        runner_rows.append({'command':command,'result':actual})
    # Deletion-only preserves upstream fallback to the recorded command.
    assert candidate['targeted_test_cmds_for_pr'](['pytest -v'],[])==['pytest -v']
    prior=ROOT.parents[2]/'30/experiments/30-script-transport'
    manifest=json.loads((prior/'live-script-manifest.json').read_text())
    frozen=[]
    for case in manifest['cases']:
        data=(prior/'inputs-private'/f"{case['pr']}-test.patch").read_bytes()
        assert hashlib.sha256(data).hexdigest()==case['test_patch_sha256']
        diff=data.decode();oldpaths=original['_files_in_patch'](diff);newpaths=selector(diff)
        assert oldpaths==case['test_files']
        commands=candidate['targeted_test_cmds_for_pr'](['cd /workspace && python -m pytest -v'],newpaths)
        if case['pr']==958:
            assert len(oldpaths)==8 and len(newpaths)==6
            assert set(oldpaths)-set(newpaths)=={'tests/similarity/test_flash_similarity_spectrum_list.py','tests/similarity/test_flash_utils_spectrum_list.py'}
        else:
            assert commands==case['commands'] and oldpaths==newpaths
        frozen.append({'pr':case['pr'],'test_patch_sha256':case['test_patch_sha256'],
                       'original_paths':oldpaths,'candidate_paths':newpaths,'candidate_commands':commands})
    with tempfile.TemporaryDirectory(prefix='biotasks32-target-patch-') as td:
        dest=Path(td)/'src/repo2rlenv/pipelines/pr_runtime.py';dest.parent.mkdir(parents=True)
        dest.write_bytes((ROOT/'upstream/pipelines/pr_runtime.py').read_bytes())
        subprocess.run(['git','apply','--check',str(ROOT/'deleted-targets.patch')],cwd=td,check=True,capture_output=True,timeout=5)
    output={'scope':'General selection fixtures and frozen Matchms patch selection, no test execution',
            'candidate_sha256':hashlib.sha256((ROOT/'candidate/pr_runtime_targeting.py').read_bytes()).hexdigest(),
            'path_cases':rows,'runner_cases':runner_rows,'deletion_only_uses_original_command':True,
            'frozen_cases':frozen,'patch_applies_to_pinned_source':True,'temporary_directory_removed':not Path(td).exists(),
            'limitations':['No live PR recovery or task export','No change to broad explicit command paths, parser, runner recognition or completion guard','Baseline reset/inventory paths remain unchanged','Deletion-only patches retain upstream whole-command fallback; no empty command is accepted']}
    (ROOT/'deleted-target-results.json').write_text(json.dumps(output,indent=2)+'\n')
    print(json.dumps({'path_cases':len(rows),'runner_cases':len(runner_rows),'frozen_cases':len(frozen),'passed':True}))


if __name__=='__main__':main()
