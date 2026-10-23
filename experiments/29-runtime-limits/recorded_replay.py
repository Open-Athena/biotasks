"""Deterministic replay of immutable recorded BASH actions, never an agent loop."""
import hashlib
import json
from pathlib import Path
import time


def replay_recorded_actions(sandbox, actions, output: Path):
    """Continue recorded failures, but stop at any divergence or client timeout.

    Caller owns sandbox creation and unconditional removal. A client timeout
    does not cancel remote commands; no subsequent command may run on that
    sandbox after this function returns a non-matching result.
    """
    assert not output.exists()
    output.mkdir(parents=True,mode=0o700)
    assert [a['step'] for a in actions]==sorted(set(a['step'] for a in actions))
    for action in actions:
        assert hashlib.sha256(action['command'].encode()).hexdigest()==action['command_sha256']
        assert action['timeout_seconds']==300
        assert 0<=action['expected_exit_code']<=255 and action['expected_exit_code']!=124
    report={'status':'running','steps':[],'commands_edited':False,'model_calls':0,'started':time.time()}
    try:
        for action in actions:
            row={k:action[k] for k in ('step','command_sha256','expected_exit_code','timeout_seconds')}
            row['started']=time.time();report['steps'].append(row)
            try:
                result=sandbox.exec(action['command'],timeout=action['timeout_seconds'])
            except Exception as error:
                row.update(exception=type(error).__name__,errno=getattr(error,'errno',None))
                report['status']='executor_exception';break
            row.update(exit_code=result.exit_code,duration_sec=result.duration_sec)
            for stream in ('stdout','stderr'):
                data=getattr(result,stream).encode();path=output/f"step-{action['step']:03d}-{stream}.txt"
                path.write_bytes(data);path.chmod(0o600)
                row[stream+'_sha256']=hashlib.sha256(data).hexdigest();row[stream+'_bytes']=len(data)
            row['finished']=time.time()
            if result.exit_code==124:
                report['status']='client_timeout_remove_sandbox';break
            if result.exit_code!=action['expected_exit_code']:
                report['status']='exit_code_divergence';break
            (output/'replay.json').write_text(json.dumps(report,indent=2)+'\n')
        else:
            report['status']='matched_recorded_exits'
    finally:
        report['finished']=time.time()
        report['unstarted_steps']=[a['step'] for a in actions[len(report['steps']):]]
        (output/'replay.json').write_text(json.dumps(report,indent=2)+'\n')
    return report
