"""Serial native batches over every frozen identity, with explicit unprocessed backlog."""

from decimal import Decimal
import json
import os
from pathlib import Path
import subprocess
import time


def save(path, value):
    temporary = path.with_suffix('.partial')
    temporary.write_text(json.dumps(value, indent=2) + '\n')
    temporary.replace(path)


def records(root):
    path = root / 'events.jsonl'
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()] if path.exists() else []


def main():
    env = os.environ.copy(); env.pop('GITHUB_TOKEN', None)
    env['PATH'] = '/work/native-bin:/work/upstream/.venv/bin:/work/bin:/usr/local/bin:/usr/bin:/bin'
    inputs = list(Path('/work/inputs').glob('*.json')); assert len(inputs) == 1
    assert not list(Path('/work/bootstrap').glob('*')), 'One fresh repository bootstrap before native cache reuse'
    identities = json.loads(Path('/work/history-identities.json').read_text())
    budget = json.loads(Path('/work/history-run-budget.json').read_text())
    env['BIOTASKS_CAMPAIGN_REMAINING_AT_REPO_START'] = budget['remaining_openrouter_usd']
    save(Path('/work/infra/history-run-budget.json'), budget)
    save(Path('/work/infra/history-identities.json'), identities)
    pending = identities['pr_numbers'].copy()
    assert len(set(pending)) == len(pending)
    deadline = float(env['BIOTASKS_NATIVE_DEADLINE_EPOCH'])
    spent, calls = Decimal('0'), 0
    ledger = {'repo': identities['repo'], 'cutoff_utc': identities['cutoff_utc'],
        'input_id_count': len(pending), 'started': time.time(), 'state': 'running',
        'batches': [], 'backlog_pr_numbers': pending.copy(), 'actual_cost_usd': '0', 'cost_complete': True}
    target = Path('/work/evidence/history-batches.json')
    save(target, ledger)
    processed = set()
    while pending:
        if time.time() + 1260 >= deadline:
            ledger['stop_reason'] = 'insufficient_remaining_native_stage_time_for_new_batch'
            break
        chosen = pending[:100]
        assert not processed.intersection(chosen)
        index = len(ledger['batches'])
        batch = {k: identities[k] for k in ['repo', 'cutoff_utc', 'source_inventory_sha256']}
        batch['pr_numbers'] = chosen
        batch_path = Path(f'/work/infra/history-batch-{index:04d}.json'); save(batch_path, batch)
        observation = Path(f'/work/native-observations/batch-{index:04d}')
        env.update(BIOTASKS_HISTORY_BATCH=str(batch_path), BIOTASKS_HISTORY_OBSERVATIONS=str(observation),
            BIOTASKS_REPO_PRIOR_COST_USD=str(spent), BIOTASKS_REPO_PRIOR_MODEL_CALLS=str(calls))
        command = ['/work/upstream/.venv/bin/python', '/work/history_entry.py', '--no-ui',
            'generate', '--config', str(inputs[0]), '--max-spend-usd', '5']
        row = {'index': index, 'selected_pr_numbers': chosen, 'command': command,
            'started': time.time(), 'state': 'running'}
        ledger['batches'].append(row); save(target, ledger)
        print(f'HISTORY_BATCH_START {identities["repo"]} index={index} selected={len(chosen)}', flush=True)
        try:
            with Path(f'/work/evidence/history-batch-{index:04d}.log').open('w') as log:
                result = subprocess.run(command, env=env, cwd='/work/upstream', stdout=log,
                    stderr=subprocess.STDOUT, check=False, timeout=max(1, deadline - time.time() - 20))
            row.update(exit_code=result.returncode, state='completed', finished=time.time())
        except subprocess.TimeoutExpired:
            row.update(state='deadline_censored', finished=time.time())
        events = records(observation)
        requested = {event['call'] for event in events if event['event'] == 'model_request'}
        charges = {event['call']: event['actual_cost_usd'] for event in events
            if event['event'] == 'model_charge' and event['actual_cost_usd'] is not None}
        assert len(charges) <= len(requested)
        spent += sum((Decimal(c) for c in charges.values()), Decimal('0')); calls += len(requested)
        returned_path = observation / 'native-candidates.json'
        returned = [r['number'] for r in json.loads(returned_path.read_text())] if returned_path.exists() else None
        entered = [e['pr'] for e in events if e['event'] == 'candidate_entered']
        assert len(set(entered)) == len(entered) and set(entered) <= set(chosen)
        assert not processed.intersection(entered)
        omitted = set(chosen) - set(returned) if returned is not None else set()
        done = set(entered) | omitted
        processed.update(done); pending = [number for number in pending if number not in done]
        row.update(native_returned_pr_numbers=returned, native_entered_pr_numbers=entered,
            native_discovery_omitted_pr_numbers=[n for n in chosen if n in omitted],
            unresolved_model_calls=sorted(requested - set(charges)))
        ledger.update(actual_cost_usd=str(spent), model_calls=calls,
            cost_complete=not row['unresolved_model_calls'], backlog_pr_numbers=pending.copy())
        save(target, ledger)
        print(f'HISTORY_BATCH_END {identities["repo"]} index={index} entered={len(entered)} backlog={len(pending)} cost={spent}', flush=True)
        stop = (row['state'] != 'completed' or not ledger['cost_complete'] or returned is None or not done
            or any(e['event'] in ['campaign_reservation_unavailable', 'history_repo_turn_stop']
                or (e['event'] == 'campaign_cost_reservation' and not e['allowed']) for e in events))
        if stop:
            ledger['stop_reason'] = 'native_acquisition_bootstrap_budget_or_deadline_boundary'
            break
    ledger.update(state='completed' if not pending else 'bounded_with_backlog', finished=time.time(),
        input_identities_accounted_for=len(processed) + len(pending) == len(identities['pr_numbers']))
    save(target, ledger)
    assert ledger['input_identities_accounted_for']


if __name__ == '__main__':
    main()
