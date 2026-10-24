"""Structural source checks only: no imports or execution of upstream modules."""
import ast
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parent


def method(path,name):
    raw=path.read_bytes();tree=ast.parse(raw)
    matches=[n for n in ast.walk(tree) if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and n.name==name]
    assert len(matches)==1,(str(path),name)
    node=matches[0]
    return node,dict(path=str(path.relative_to(ROOT)),function=name,line_start=node.lineno,line_end=node.end_lineno,
        file_sha256=hashlib.sha256(raw).hexdigest(),ast_sha256=hashlib.sha256(ast.dump(node,include_attributes=False).encode()).hexdigest())


def calls(node,name):
    return [n for n in ast.walk(node) if isinstance(n,ast.Call) and ast.unparse(n.func)==name]


def handlers(node):
    return [ast.unparse(n.type) if n.type else 'bare' for n in ast.walk(node) if isinstance(n,ast.ExceptHandler)]


def main():
    old,oldspan=method(ROOT/'inputs-private/baseline/harbor/trial/trial.py','_verify_with_retry')
    assert any(isinstance(n,ast.Call) and ast.unparse(n.func)=='retry' for n in old.decorator_list)
    assert 'stop_after_attempt(2)' in ast.unparse(old)
    records=[]
    for label in ['release','main']:
        base=ROOT/'inputs-private'/label/'src/harbor';spans=[]
        def get(relative,name):
            node,span=method(base/relative,name);spans.append(span);return node
        single=get('trial/single_step.py','_run_verifier')
        assert not any(isinstance(n,(ast.For,ast.While,ast.AsyncFor)) for n in ast.walk(single))
        assert all(ast.unparse(d)=='override' for d in single.decorator_list)
        assert len(calls(single,'self._run_shared_verifier'))==1 and len(calls(single,'self._run_separate_verifier'))==1
        run=get('trial/single_step.py','_run')
        assert len(calls(run,'self._run_verifier'))==1
        timeout=get('trial/trial.py','_verify_with_timeout')
        assert len(calls(timeout,'asyncio.wait_for'))==1 and len(calls(timeout,'verifier.verify'))==1
        assert not timeout.decorator_list
        buffered=get('environments/docker/docker.py','_collect_buffered_output')
        streamed=get('environments/docker/docker.py','_collect_streamed_output')
        terminate=get('environments/docker/docker.py','_terminate_process')
        assert handlers(buffered)==['asyncio.TimeoutError']
        assert handlers(streamed)==['asyncio.TimeoutError','BaseException']
        assert calls(terminate,'process.terminate') and calls(terminate,'process.kill')
        assert not any('docker' in ast.unparse(n.func).lower() for n in ast.walk(terminate) if isinstance(n,ast.Call))
        verifier=get('verifier/verifier.py','verify')
        invocations=calls(verifier,'self.environment.exec')
        assert invocations and not any(k.arg=='timeout_sec' for n in invocations for k in n.keywords)
        log=get('trial/trial.py','_log_context')
        assert calls(log,'contextlib.nullcontext') and calls(log,'environment.scoped_output_callback')
        command=get('utils/scripts.py','build_execution_command')
        assert ') > ' in ast.unparse(command)
        path=get('models/trial/paths.py','test_stdout_path')
        assert 'test-stdout.txt' in ast.unparse(path)
        recover=get('trial/single_step.py','_recover_outputs')
        assert calls(recover,'self._stop_agent_environment') and not calls(recover,'self._run_verifier')
        stop=get('trial/trial.py','_stop_agent_environment')
        assert calls(stop,'asyncio.shield')
        records.append(dict(label=label,claims=dict(single_step_automatic_inner_verifier_retry=False,
            one_verifier_branch_invocation=True,outer_wait_for_still_used=True,verifier_passes_inner_exec_timeout=False,
            buffered_outer_cancellation_handler=False,streamed_base_exception_handler=True,
            termination_helper_targets_cli_subprocess=True,daemon_process_termination_proven=False,
            streaming_opt_in=True,fixed_per_trial_stdout_truncation=True,error_recovery_stops_environment=True),source_spans=spans))
    report=dict(issue=42,baseline_retry_decorator=oldspan,baseline_native_evidence_issue=41,
        records=records,source_only=True,upstream_imported_or_executed=False,selected_upstream_tests_run=False,
        native_runtime_cpu_hours=0,model_calls=0,new_biological_tasks=0,
        conclusion='Published 0.24.0 and pinned main remove the old single-step inner retry, but source does not establish daemon-side cancellation or universal per-attempt log isolation. Candidate for a separate native comparison, not an approved production upgrade.',
        limits='Structural assertions establish inspected call paths, not Docker daemon outcomes. Selected test review is bounded, not exhaustive. Package runtime-source parity is recorded separately; current main is unreleased source.')
    (ROOT/'source-assessment.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(revisions_checked=len(records),source_functions_checked=sum(len(r['source_spans']) for r in records)+1,upstream_executed=False)))


if __name__=='__main__':main()
