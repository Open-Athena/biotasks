"""Verify only the completed generation with the original installed implementation."""
import json
import sys
from pathlib import Path
from biotasks.generation.finish_generation import generation_ready
from biotasks.validation.files import inventory,sha

root=Path(__file__).resolve().parent
work=root/'inputs-private/run-001/dendropy'
ledger=root.parents[2]/'33/experiments/33-unattended-validation/budget.json'
before=inventory(work);cost=sha(ledger)
def audit(event,args):
    if event in {'socket.connect','socket.getaddrinfo','subprocess.Popen','os.system','os.exec','os.posix_spawn'}:
        raise AssertionError('Completed generation must remain local')
    if event=='open' and isinstance(args[0],(str,bytes)) and any(x in str(args[0]) for x in ['/.codex/secrets/','/.config/coreweave/','/.cache/huggingface/token']):
        raise AssertionError('Completed generation must not read credentials')
sys.addaudithook(audit)
ready=generation_ready(work)
assert ready['state']=='ready' and ready['readback']['model_billing']['complete']
assert inventory(work)==before and sha(ledger)==cost
proof=dict(state='completed_generation_verified; full connector held',actual_original_installed_implementation=True,completed_generation_byte_inert=True,transport_and_credential_reads_forbidden=True,budget_sha256=cost,generation_binding=ready['binding'],model_billing=ready['readback']['model_billing'],exported_tasks=ready['readback']['exported_tasks'],scientific_acceptance=False,native_controls_submitted=0,new_jobs_or_calls=0)
(root/'completed-generation-proof.json').write_text(json.dumps(proof,indent=2)+'\n')
print(json.dumps({k:v for k,v in proof.items() if k!='generation_binding'},indent=2))
