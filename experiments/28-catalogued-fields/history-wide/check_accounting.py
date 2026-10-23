"""Offline accounting boundary fixtures; no model, GitHub, Docker or Iris calls."""

from copy import deepcopy
from decimal import Decimal
import io
import json
from pathlib import Path
import tarfile
from tempfile import TemporaryDirectory

from audit_accounting import ROOT, audit_calls, phase_records
from cost_guard import reservation


QUOTE = json.loads((ROOT / 'openrouter-endpoints.json').read_text())['response']


def batch(index, prior, cost, *, generation=False):
    root = f'native-observations/batch-{index:04d}/'
    available = Decimal('20') - prior
    amount = reservation(QUOTE, 2048)
    events = [
        {'event': 'campaign_cost_reservation', 'available_usd': str(available),
         'reserved_usd': str(amount), 'allowed': available >= amount, 'time': index * 10 + 1},
        {'event': 'model_request', 'call': 1, 'model': 'openrouter/anthropic/claude-sonnet-4.6',
         'max_tokens': 2048, 'temperature': 0.2, 'time': index * 10 + 2},
        {'event': 'model_response', 'call': 1, 'response_id': f'fixture-{index}',
         'usage': {'cost': str(cost)}, 'time': index * 10 + 3},
        {'event': 'model_charge', 'call': 1, 'actual_cost_usd': str(cost),
         'cumulative_actual_usd': str(cost), 'time': index * 10 + 4,
         'source': 'generation.total_cost' if generation else 'response.usage.cost'},
    ]
    records = {root + 'events.jsonl': events, root + 'cost-quote-001.json': deepcopy(QUOTE),
        root + 'billing.json': {'cost_complete': True, 'shared_account_deltas_used': False,
            'actual_cost_usd': str(cost), 'model_calls': 1, 'stop_threshold_usd': str(Decimal('5') - prior)}}
    if generation:
        records[root + 'generation-001.json'] = {'id': f'fixture-{index}', 'total_cost': str(cost)}
    return records


def rejected(records):
    try:
        audit_calls(records, Decimal('20'))
    except (AssertionError, KeyError):
        return
    raise AssertionError('Invalid original accounting evidence was accepted')


def main():
    original = batch(0, Decimal('0'), Decimal('4.99'))
    original.update(batch(1, Decimal('4.99'), Decimal('0.20'), generation=True))
    row = audit_calls(original, Decimal('20'))
    assert row['actual_cost_usd'] == '5.19' and row['model_calls'] == 2
    assert row['all_dispatched_calls_reconciled']
    extra = deepcopy(original); extra.update(batch(2, Decimal('5.19'), Decimal('0.01')))
    rejected(extra)  # The allowed final-request overshoot cannot permit another call.
    turns = {}
    for index in range(20):
        turns.update(batch(index, Decimal(index) / 100, Decimal('0.01')))
    assert audit_calls(turns, Decimal('20'))['model_calls'] == 20
    turns.update(batch(20, Decimal('0.20'), Decimal('0.01')))
    rejected(turns)
    for alter in ['pending', 'wrong_cost', 'wrong_reservation', 'reset_threshold', 'duplicate_response', 'wrong_call_number']:
        broken = deepcopy(original)
        first = broken['native-observations/batch-0000/events.jsonl']
        second = broken['native-observations/batch-0001/events.jsonl']
        if alter == 'pending':
            first.pop()
        elif alter == 'wrong_cost':
            first[2]['usage']['cost'] = '0'
        elif alter == 'wrong_reservation':
            first[0]['reserved_usd'] = '1'
        elif alter == 'reset_threshold':
            broken['native-observations/batch-0001/billing.json']['stop_threshold_usd'] = '5'
        elif alter == 'duplicate_response':
            second[2]['response_id'] = first[2]['response_id']
        else:
            first[1]['call'] = 2
        rejected(broken)
    empty = {'native-observations/batch-0000/billing.json': {'cost_complete': True,
        'shared_account_deltas_used': False, 'actual_cost_usd': '0', 'model_calls': 0, 'stop_threshold_usd': '5'}}
    assert audit_calls(empty, Decimal('20'))['model_calls'] == 0
    with TemporaryDirectory(prefix='history-accounting-check-') as temporary:
        path = Path(temporary) / 'phase.tar.gz'
        records = {'infra/history-run-budget.json': b'{"remaining_openrouter_usd":"20"}',
            'native-observations/batch-0000/billing.json': json.dumps(empty['native-observations/batch-0000/billing.json']).encode(),
            'outputs/task/source.txt': b'ignored original source'}
        with tarfile.open(path, 'w:gz') as archive:
            for name, raw in records.items():
                member = tarfile.TarInfo(name); member.size = len(raw); archive.addfile(member, io.BytesIO(raw))
        observed = phase_records(path)
        assert set(observed) == set(records) - {'outputs/task/source.txt'}
        assert audit_calls(observed, Decimal('20'))['actual_cost_usd'] == '0'
    print('Accounting fixtures passed: cumulative cross-batch turn/cost guards, allowed final-request overshoot, original response/generation charges, exact route reservations, pending-call rejection, unique request/response identities, zero-call snapshots and streaming original-record selection. No model/API/job/test execution; scratch removed.')


if __name__ == '__main__':
    main()
