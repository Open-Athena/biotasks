"""Use pinned upstream pure functions; retain generated script/patch bytes privately."""
import ast,hashlib,json,re,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parent


def load(path,names,namespace):
    tree=ast.parse(path.read_text())
    nodes=[n for n in tree.body if (isinstance(n,ast.FunctionDef) and n.name in names) or (isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id in names for t in n.targets))]
    exec(compile(ast.Module(body=nodes,type_ignores=[]),str(path),'exec'),namespace)


def sha(data):return hashlib.sha256(data).hexdigest()


def main():
    source=ROOT/'upstream/pipelines/pr_runtime.py'
    stage=ROOT/'upstream/pipelines/pr_runtime_validate.py'
    assert sha(source.read_bytes())=='0b748a897f1802fcaf4b59ab7ed54092c8715745b5dff14813c6389b1e134535'
    assert sha(stage.read_bytes())=='1f8349718bc93315bf3e5cbb10d5823c832539a8ef680b5ee169e4562de3ea49'
    ns={'re':re}
    load(source,{'_TEST_DIR_NAMES','_DOC_PREFIX_DIRS','_DIFF_HEADER_RE','_path_is_test','split_patch_and_test_patch','_files_in_patch','normalize_test_cmds_for_runtime','_PYTEST_TARGETABLE_EXT','_JEST_TARGETABLE_EXT','_go_packages_from_test_files','targeted_test_cmds_for_pr'},ns)
    load(stage,{'_HEREDOC','_heredoc_apply','_build_stage_script'},ns)
    records=[]
    acquired={r['pr']:r for r in json.loads((ROOT/'live-case-acquisition.json').read_text())['rows']}
    for case in json.loads((ROOT/'live-cases.json').read_text())['cases']:
        identity=case['identity'];number=identity['number'];record=acquired[number]
        for key in ['base_sha','head_sha']:assert record['current_metadata'][key]==identity[key]
        raw=(ROOT/record['diff']['path']).read_bytes();assert sha(raw)==record['diff']['sha256']
        diff=raw.decode();paths=ns['_files_in_patch'](diff)
        assert set(paths)==set(identity['changed_files'])
        patch,test_patch=ns['split_patch_and_test_patch'](diff)
        tests=ns['_files_in_patch'](test_patch)
        commands=ns['targeted_test_cmds_for_pr'](ns['normalize_test_cmds_for_runtime'](['cd /workspace && python -m pytest -v']),tests)
        row={'pr':number,'base_sha':identity['base_sha'],'head_sha':identity['head_sha'],'diff_sha256':sha(raw),'source_patch_bytes':len(patch.encode()),'test_patch_bytes':len(test_patch.encode()),'source_patch_sha256':sha(patch.encode()),'test_patch_sha256':sha(test_patch.encode()),'test_files':tests,'commands':commands,'stages':{}}
        for side in ['pre','post']:
            script=ns['_build_stage_script'](identity['base_sha'],apply_patch=patch if side=='post' else None,apply_test_patch=test_patch,test_cmds=commands)
            data=script.encode();path=ROOT/'inputs-private'/f'{number}-{side}.sh';path.write_bytes(data);path.chmod(0o600)
            result=subprocess.run(['bash','-n',str(path)],capture_output=True,text=True,timeout=5);assert result.returncode==0
            row['stages'][side]={'bytes':len(data),'sha256':sha(data),'bash_syntax_exit':result.returncode,'exceeds_128k_linux_argument_limit':len(data)>=131072}
        for name,data in [('source.patch',patch),('test.patch',test_patch)]:
            path=ROOT/'inputs-private'/f'{number}-{name}';path.write_text(data);path.chmod(0o600)
        records.append(row)
    (ROOT/'live-script-manifest.json').write_text(json.dumps({'scope':'Pinned-ref diffs rendered by unchanged upstream splitter, targeting and stage builders; syntax-only checks; no script execution or PR recovery','pipeline_source_sha256':sha(source.read_bytes()),'stage_source_sha256':sha(stage.read_bytes()),'cases':records,'limits':['Original failed script bytes not retained; reconstructed inputs bound here','No timeout/parser/rebuild changes included','128 KiB comparison describes typical Linux single-argument boundary, not a live Docker result']},indent=2)+'\n')
    print(json.dumps([{'pr':r['pr'],'stage_bytes':{k:v['bytes'] for k,v in r['stages'].items()}} for r in records]))

if __name__=='__main__':main()
