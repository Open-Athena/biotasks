"""Offline solver gating/configuration checks; no provider or model calls."""
import copy
import json
import tempfile
from pathlib import Path
from harbor.models.task.task import Task
from run_pr_blind_solver import check_controls, solver_config

root=Path(__file__).resolve().parent
baseline=root/'evidence/pr-provider-02/baseline-result.json'
base=json.loads(baseline.read_text())
assert Task(root/'evidence/marin-pr2633-preparation/harbor-task').checksum == base['task_checksum']
with tempfile.TemporaryDirectory() as temp:
    temp=Path(temp)
    spec=solver_config(root/'evidence/marin-pr2633-preparation/harbor-task',temp,'https://example.invalid/v1')
    assert spec.agent.model_name=='openai/glm-5.3'
    assert spec.agent.override_timeout_sec==900
    assert spec.agent.kwargs['max_turns']==12
    assert spec.agent.kwargs['llm_call_kwargs']=={'max_tokens':2048}
    assert spec.environment.override_cpus==2 and spec.environment.override_memory_mb==4096
    assert spec.environment.override_storage_mb==10240 and spec.environment.delete
    ref_result=copy.deepcopy(base)
    ref_result['verifier_result']['rewards']['reward']=1
    fixture={'status':'passed','model_calls':0,'cases':[{'agent':'oracle','result':ref_result}]}
    ref=temp/'synthetic-reference.json'
    def write(value):ref.write_text(json.dumps(value))
    write(fixture)
    assert check_controls(baseline,ref)==base['task_checksum']
    for mutate in [lambda x:x.update(status='failed'),lambda x:x.update(model_calls=1),lambda x:x['cases'][0]['result'].update(task_checksum='wrong'),lambda x:x['cases'][0]['result']['verifier_result']['rewards'].update(reward=0)]:
        invalid=copy.deepcopy(fixture);mutate(invalid);write(invalid)
        try:check_controls(baseline,ref)
        except AssertionError:pass
        else:raise AssertionError('Invalid control evidence accepted')
print('PASS: exact local/control task identity; approved solver settings; failed, model-using, mismatched and incorrect reference controls rejected. Synthetic reference only; no live reference claim.')
