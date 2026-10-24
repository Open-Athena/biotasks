"""Execute exact upstream function bodies against small filesystem fixtures."""
import ast
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import tempfile

from resolver_candidate import AmbiguousRecipe,resolve

ROOT=Path(__file__).resolve().parent
PRIOR=ROOT.parents[2]/'31/experiments/31-historical-builds'


def digest(data):return hashlib.sha256(data).hexdigest()


def functions(path,names,namespace):
    source=path.read_text();tree=ast.parse(source);hashes={}
    for name in names:
        node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name==name)
        code=ast.get_source_segment(source,node)
        hashes[name]=digest(code.encode())
        exec(compile('from __future__ import annotations\n'+code,str(path),'exec'),namespace)
    return hashes


def main():
    acquisition=json.loads((PRIOR/'package-acquisition.json').read_text())
    source=PRIOR/'inputs-private/upstream-package'
    for row in acquisition['files']:
        assert digest((source/row['path']).read_bytes())==row['sha256']
    latest=json.loads((ROOT/'current-upstream-source.json').read_text())
    for row in latest['files']:
        raw=(ROOT/'inputs-private/current-upstream'/row['path']).read_bytes()
        assert digest(raw)==row['sha256']
    blocked=[]
    def audit(event,args):
        if event in ('socket.connect','socket.getaddrinfo','subprocess.Popen','os.system'):
            blocked.append(event);raise AssertionError(event)
        if event=='open' and isinstance(args[0],str):
            path=str(Path(args[0]).resolve())
            if any(name in path for name in ('.codex/secrets/','.config/gh/','.config/coreweave/','.cache/huggingface/token','.git-credentials','.docker/config.json')):
                blocked.append('credential_store_open');raise AssertionError('Credential store access')
    sys.addaudithook(audit)
    namespaces=[];fingerprints=[]
    for tree in [source,ROOT/'inputs-private/current-upstream']:
        namespace=dict(Path=Path,re=re,json=json,hashlib=hashlib,_LANG_BASE_IMAGE={'python':'python:3.12-slim'})
        hashes=functions(tree/'src/repo2rlenv/bootstrap/cache.py',['_options_hash','cache_key'],namespace)
        hashes.update(functions(tree/'src/repo2rlenv/registry/integration.py',
            ['_parse_local_tag','_build_clean_recipe','_load_bootstrap_recipe'],namespace))
        namespaces.append(namespace);fingerprints.append(hashes)
    assert fingerprints[0]==fingerprints[1], 'Reassess changed upstream functions before proceeding'
    native=namespaces[0];rows=[];cwd=Path.cwd()
    with tempfile.TemporaryDirectory(prefix='identity-fixtures-',dir=ROOT/'inputs-private') as td:
        def run_case(name,repo='foo/bar',root='workspace/bootstrap',options=None,
                     absent=False,conflict=None,ambiguous=False,custom=False):
            case=Path(td)/name;case.mkdir();os.chdir(case)
            ref='a'*40;tag='local/r2e-bootstrap/'+repo.replace('/','__').lower()+':'+ref[:12]
            if not absent:
                slot=native['cache_key'](repo,ref,Path(root),options=options)
                slot.mkdir(parents=True)
                data=dict(repo=repo,ref=ref,image_tag=tag,language='python',
                    dockerfile_reconstruction='FROM python:3.12-slim\n',rebuild_cmds=['echo original'],test_cmds=['pytest'])
                if conflict=='repo':data['repo']='other/repo'
                if conflict=='ref':data['ref']='b'*40
                (slot/'bootstrap.json').write_text(json.dumps(data))
                if ambiguous:
                    other=native['cache_key'](repo,ref,Path(root),options={'base_image':'python:3.11-slim'})
                    other.mkdir(parents=True);(other/'bootstrap.json').write_text(json.dumps(dict(data,rebuild_cmds=['echo alternative'])))
            before=native['_load_bootstrap_recipe'](tag)
            try:
                after=resolve(tag,native['_parse_local_tag'],native['_build_clean_recipe'],
                    cache_dir=Path(root) if custom else None)
                candidate_state='resolved' if after[0] else 'unavailable'
            except AmbiguousRecipe:
                after=(None,None);candidate_state='ambiguous rejected'
            row=dict(case=name,baseline_state='resolved' if before[0] else 'unavailable',
                candidate_state=candidate_state,baseline_recipe_sha256=digest(before[0].encode()) if before[0] else None,
                candidate_recipe_sha256=digest(after[0].encode()) if after[0] else None)
            rows.append(row)
            if name in ('lowercase','legacy_lowercase','single_option_slot'):
                assert before==after and before[0]
            if name in ('mixed_case','legacy_mixed_case','explicit_custom_root'):
                assert not before[0] and after[0]
            if name=='missing':assert before==after==(None,None)
            if conflict:assert before[0] and not after[0]
            if ambiguous:assert before[0] and candidate_state=='ambiguous rejected'
        try:
            run_case('lowercase');run_case('mixed_case',repo='OHIF/Viewers')
            run_case('legacy_lowercase',root='envs');run_case('legacy_mixed_case',repo='OHIF/Viewers',root='envs')
            run_case('explicit_custom_root',root='custom-cache',custom=True)
            run_case('missing',absent=True);run_case('single_option_slot',options={'base_image':'python:3.12-slim'})
            run_case('multiple_option_slots',options={'base_image':'python:3.12-slim'},ambiguous=True)
            run_case('metadata_repo_conflict',conflict='repo');run_case('metadata_ref_conflict',conflict='ref')
        finally:os.chdir(cwd)
    report=dict(scope='Function-level fixtures; no complete bootstrap, Docker build or task execution',
        baseline_revision=acquisition['revision'],latest_revision=latest['revision'],
        relevant_upstream_functions_identical=True,function_source_sha256=fingerprints[0],cases=rows,
        fixture_cases_passed=len(rows),blocked_operations=blocked,model_calls=0,docker_commands=0,
        owned_fixture_directories_removed=True)
    (ROOT/'fixture-results.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ('cases','function_source_sha256')}))


if __name__=='__main__':main()
