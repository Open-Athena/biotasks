"""Read the actual sealed original generation from a clean installed consumer."""
import json
import sys
from pathlib import Path
from biotasks.generation import resources
from biotasks.generation.finish_generation import generation_ready
from biotasks.generation.run_generation import run
from biotasks.validation.files import inventory,sha,ValidationError

root=Path(__file__).resolve().parent
runner=root/'inputs-private/candidate-runner'
assert Path(resources.__file__).resolve().is_relative_to(runner)
old=root.parents[2]/'62/experiments/62-fresh-dendropy/inputs-private/run-001/dendropy'
ledger=root.parents[2]/'33/experiments/33-unattended-validation/budget.json'
before,cost=inventory(old),sha(ledger)
def audit(event,args):
    if event in {'socket.connect','socket.getaddrinfo','subprocess.Popen','os.system','os.exec','os.posix_spawn'}:
        raise AssertionError('Sealed import must remain local/read-only')
    if event=='open' and isinstance(args[0],(str,bytes)):
        if any(x in str(args[0]) for x in ['/.codex/secrets/','/.config/coreweave/','/.cache/huggingface/token']):
            raise AssertionError('Sealed import must not read credentials')
        mode=args[1]
        if isinstance(mode,str) and any(c in mode for c in 'wax+'):
            raise AssertionError('Sealed import must not open files for writing')
sys.addaudithook(audit)
ready=generation_ready(old)
assert ready['state']=='ready' and ready['binding']['read_only_completed_import']
assert ready['binding']['original_generation_code_identity']=='eeda76c4fb1dc7c18d4699ea542d03b63cad13f5d9c0a1ed1df8f87faedfdfee'
try:run(old,once=True)
except ValidationError as e:assert 'implementation changed' in str(e)
else:raise AssertionError('Old generation must never be resumed under new code')
assert inventory(old)==before and sha(ledger)==cost
# The audit deliberately forbids writes; emit the report to stdout for the harness.
print(json.dumps(dict(state='sealed_import_verified',actual_installed_module=resources.__file__,consumer_identity=resources.code_identity(),generation_binding=ready['binding'],exported_tasks=ready['readback']['exported_tasks'],billing=ready['readback']['model_billing'],old_generation_and_budget_byte_inert=True,transport_credential_reads_and_file_writes_forbidden=True,old_generation_run_rejected=True,native_or_model_calls=0,scientific_acceptance=False),indent=2))
