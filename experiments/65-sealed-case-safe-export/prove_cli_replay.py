"""Actual installed planner/export replay remains byte-inert and offline."""
import io,json,sys
from contextlib import redirect_stdout
from pathlib import Path
from biotasks.cli import main
from biotasks.generation import resources
from biotasks.validation.files import inventory,sha

root=Path(__file__).resolve().parent;work=root/'inputs-private/import-001'
old=root.parents[2]/'62/experiments/62-fresh-dendropy/inputs-private/run-001/dendropy'
ledger=root.parents[2]/'33/experiments/33-unattended-validation/budget.json'
assert Path(resources.__file__).resolve().is_relative_to(root/'inputs-private/candidate-runner')
before,original,cost=inventory(work),inventory(old),sha(ledger)
def audit(event,args):
    if event in {'socket.connect','socket.getaddrinfo','subprocess.Popen','os.system','os.exec','os.posix_spawn'}:raise AssertionError('Replay attempted external operation')
    if event=='open' and isinstance(args[0],(str,bytes)) and any(x in str(args[0]) for x in ['/.codex/secrets/','/.config/coreweave/','/.cache/huggingface/token']):raise AssertionError('Replay read credentials')
sys.addaudithook(audit)
outputs=[]
for args in [['generate','plan',str(root/'manifest.json'),'--work-dir',str(work)],['generate','run',str(work),'--once']]:
 out=io.StringIO()
 with redirect_stdout(out):
  try:main(args)
  except SystemExit as e:assert e.code in (None,0)
 outputs.append(json.loads(out.getvalue()))
assert outputs[1]==json.loads((root/'local-export-summary.json').read_text())
assert inventory(work)==before and inventory(old)==original and sha(ledger)==cost
print(json.dumps(dict(actual_installed_module=resources.__file__,generation_code_identity=resources.code_identity(),plan_identity=outputs[0]['plan_identity'],local_export_state=outputs[1]['state'],original_and_consumer_and_budget_byte_inert=True,transport_and_credential_reads_forbidden=True,new_native_or_model_calls=0,scientific_acceptance=False),indent=2))
