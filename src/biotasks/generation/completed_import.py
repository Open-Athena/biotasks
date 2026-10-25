"""Read-only verification of known, fully sealed earlier generation profiles.

This path cannot submit, observe, reconcile, repair or complete an old run.
Normal resume still requires the current implementation identity.
"""
from importlib.resources import files
from pathlib import Path
from typing import Any
import json

from biotasks.generation import model_budget
from biotasks.generation.generation_pipeline import GenerationPipeline
from biotasks.validation.files import json_sha, read_json, require, sha
from biotasks.validation.journal import Binding, STAGES


def profiles() -> list[dict[str, Any]]:
    return json.loads((files('biotasks.generation') / 'completed-profiles.json').read_bytes())


def verify(root: Path, plan: dict[str, Any]) -> None:
    matches = [p for p in profiles()
               if p['generation_code_identity'] == plan.get('generation_code_identity')
               and p['validation_code_identity'] == plan['validation_code_identity']]
    require(len(matches) == 1, 'Unsupported completed generation profile')
    group = plan['group']
    require(group['id'] == 'generation', 'Unsupported completed generation group')
    require(all(group['payload_sha256'].get(k) == v
                for k, v in matches[0]['assets_sha256'].items()),
            'Completed generation assets differ from known profile')
    directory = root / 'runs/generation'
    require(directory.is_dir() and not directory.is_symlink(), 'Missing completed generation')
    journal = read_json(directory / 'journal.json')
    require(not journal.get('intent') and
            [r['stage'] for r in journal['stages']] == list(STAGES),
            'Only fully completed generations may be imported')
    require(not any((base/name).exists() for base in (directory,directory/'cleanup',directory/'stop') for name in ('held.json','budget-hold.json','model-budget-hold.json')),
            'Held generation cannot be imported')
    require(journal['run_id'] == group['run_id'] and journal['plan_sha256'] == json_sha({
        'run_id': group['run_id'],
        'inputs': [Binding(str(root/'plan.json'), sha(root/'plan.json')).json()],
        'stages': STAGES,
    }), 'Completed generation journal identity changed')
    # Verification methods share the unchanged validation lifecycle. No step(),
    # probe(), perform() or recovery is called and no journal lock is opened.
    pipeline = GenerationPipeline(root, plan, group)
    for record in journal['stages']:
        evidence = tuple(Binding(**e) for e in record['evidence'])
        require(bool(evidence), 'Completed stage has no evidence')
        for item in evidence:
            item.verify()
        pipeline.verify(record['stage'], evidence)
    readback = read_json(directory/'readback.json')
    if readback['source_members']:
        from biotasks.generation.finish_generation import verify_generation_source

        verify_generation_source(directory, readback)
    bill = readback['model_billing']
    require(bill['complete'] is True, 'Completed generation billing unresolved')
    ledger = read_json(Path(plan['budget_ledger']))
    model = [e for e in ledger['events'] if e['kind'] == 'model_run_reservation'
             and e['run_id'] == group['run_id']]
    require(len(model) == 1 and model[0]['state'] == 'terminal reconciled'
            and model[0]['call_count_complete'] is True
            and model[0]['known_calls'] == bill['calls']
            and model_budget.amount(model[0]['known_actual_usd']) == model_budget.amount(bill['known_actual_usd'])
            and model_budget.amount(model[0]['outstanding_usd']) == 0,
            'Completed generation model reservation unresolved')
    ids = {group['run_id'], group['run_id']+'-stop', group['run_id']+'-cleanup'}
    cpu = [e for e in ledger['events'] if e['kind'] == 'reserved_cpu_admission' and e['run_id'] in ids]
    require(len(cpu) == 3 and {e['run_id'] for e in cpu} == ids
            and all(e['state'] in {'terminal reconciled', 'released unused'} for e in cpu),
            'Completed generation CPU reservations unresolved')
