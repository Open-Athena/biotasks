"""Pin source facts and fake-transport evidence without claiming Docker behavior."""
import ast
import hashlib
import json
from pathlib import Path
import sys

from native_loader import sha

ROOT=Path(__file__).resolve().parent


def symbol(path,owner,name):
    raw=path.read_text();tree=ast.parse(raw)
    parent=tree if owner is None else next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name==owner)
    node=next(n for n in parent.body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and n.name==name)
    return node,dict(path=str(path.relative_to(ROOT/'inputs-private/source')),symbol=(owner+'.' if owner else '')+name,
        line=node.lineno,end_line=node.end_lineno,file_sha256=sha(path),symbol_source_sha256=hashlib.sha256(ast.get_source_segment(raw,node).encode()).hexdigest())


def main():
    acquisition=json.loads((ROOT/'package-acquisition.json').read_text());source=ROOT/'inputs-private/source'
    assert acquisition['wheel_sha256']=='30477bf698d6853d6c4bb76d85aec85e1e95190ad3a6e4bf4730435926007652'
    for row in acquisition['source_files']:assert sha(source/row['path'])==row['sha256']
    checks=json.loads((ROOT/'cancellation-checks.json').read_text());assert checks['successful'] and checks['checks_run']==3 and checks['real_subprocesses_started']==0
    docker=source/'harbor/environments/docker/docker.py';trial=source/'harbor/trial/trial.py';verifier=source/'harbor/verifier/verifier.py';scripts=source/'harbor/utils/scripts.py'
    process,p1=symbol(docker,'DockerEnvironment','_run_docker_compose_command')
    blocks=[n for n in ast.walk(process) if isinstance(n,ast.Try)];assert len(blocks)==2
    assert [ast.unparse(h.type) for h in blocks[0].handlers]==['asyncio.TimeoutError'] and not blocks[0].finalbody
    invoke,p2=symbol(verifier,'Verifier','verify')
    exec_calls=[n for n in ast.walk(invoke) if isinstance(n,ast.Call) and ast.unparse(n.func)=='self._environment.exec']
    assert len(exec_calls)==2 and not any(k.arg=='timeout_sec' for call in exec_calls for k in call.keywords)
    retry,p3=symbol(trial,'Trial','_verify_with_retry');decorator=ast.unparse(retry.decorator_list[0])
    assert 'stop_after_attempt(2)' in decorator and 'min=1' in decorator
    assert not any(isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr=='stop' for n in ast.walk(retry))
    run,p4=symbol(trial,'Trial','run');assert any(isinstance(n,ast.Try) and any('_cleanup_and_finalize' in ast.unparse(s) for s in n.finalbody) for n in ast.walk(run))
    command,p5=symbol(scripts,None,'build_execution_command');assert ') > ' in scripts.read_text()
    caps,p6=symbol(docker,'DockerEnvironment','capabilities');assert 'mounted=True' in ast.unparse(caps)
    dependency=json.loads((ROOT/'test-dependency-acquisition.json').read_text());assert dependency['version']=='9.2.1'
    result=dict(issue=41,kind='Pinned source and selected native AST under fake process transport',package_wheel_sha256=acquisition['wheel_sha256'],version='0.6.6',source_files_verified=len(acquisition['source_files']),symbols=[p1,p2,p3,p4,p5,p6],
        facts=dict(verifier_deadline='Trial asyncio.wait_for around verifier.verify',inner_docker_exec_timeout_supplied=False,
            docker_helper_timeout_handler='Catches its internal TimeoutError, terminates/kills only its client subprocess; no CancelledError/finally handler',
            native_verifier_attempts=2,retry_minimum_delay_seconds=1,environment_stopped_between_attempts=False,environment_stop='Trial.run finalization after retry loop',
            verifier_stdout_redirect='Truncating shell redirection to the same per-trial file',linux_logs_directly_mounted=True),
        checks_sha256=sha(ROOT/'cancellation-checks.json'),checks_run=3,selected_native_ast_executed=True,process_transport='fake',
        dependency_version='9.2.1',dependency_wheel_sha256=dependency['wheel_sha256'],local_python=sys.version,
        interpretation='Outer cancellation misses the helper termination branch; retry reuses the environment. This makes surviving writers plausible but does not demonstrate daemon-side survival or historical log-hole causation.',
        required_native_evidence=['Observe first writer PID/start time/FD after native first deadline and during retry','Tie same-inode truncation and writer offsets to any NUL holes','Compare with a finite normal-completion fixture using the same native path','Preserve raw events/log bytes before ownership-scoped teardown'],
        no_original_task_changes=True,real_subprocesses_started=0,remote_jobs=0,model_calls=0,
        retained_paths=[dict(path='inputs-private/harbor-0.6.6-py3-none-any.whl',reason='Exact pinned package for source/runtime parity',cleanup_condition='Remove duplicate after runtime/evidence archival and source availability verification'),
            dict(path='inputs-private/source',reason='Pinned source for parity checks and source references',cleanup_condition='After verified archival/reproducibility'),
            dict(path='inputs-private/check-dependency',reason='Original exact Tenacity wheel/source for isolated tests and runtime pin',cleanup_condition='After verified archival/reproducibility')],task_owned_tmp_paths=[])
    (ROOT/'source-assessment.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(source_files_verified=203,checks=3,process_transport='fake',native_docker_proven=False,remote_jobs=0,model_calls=0)))


if __name__=='__main__':main()
