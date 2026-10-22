"""Offline source-level integration and budget-boundary checks; no live model call."""

from decimal import Decimal
import importlib.util
import io
import json
from pathlib import Path
import sys
from unittest.mock import patch

import cost_guard
import discovery_adapter
from payload import BASE, build

ROOT = Path(__file__).resolve().parent


class Recorder:
    def __init__(self):
        self.actual_cost = Decimal('0'); self.threshold = Decimal('5')
        self.cost_unknown = False; self.calls = 0; self.events = []

    def event(self, name, **fields):
        self.events.append((name, fields))

    def save(self, *args, **kwargs):
        pass


def main():
    spec = importlib.util.spec_from_file_location('pinned_native_github', ROOT / 'pinned-github.py')
    module = importlib.util.module_from_spec(spec); sys.modules[spec.name] = module; spec.loader.exec_module(module)
    original_list = module.list_merged_prs
    seen = []

    def fake(args, token=None):
        seen.append(args)
        if args[:2] == ['pr', 'view']:
            number = int(args[2])
            return json.dumps({'number': number, 'title': 'Fix example', 'body': 'Exact body',
                'state': 'MERGED', 'mergedAt': '2020-01-01T00:00:00Z', 'baseRefName': 'main',
                'headRefOid': 'a' * 40, 'isDraft': number == 1202, 'url': f'https://github.com/a/b/pull/{number}',
                'files': [{'path': 'tests/test_example.py'}]})
        if args[:1] == ['api']:
            if args[1].endswith('/1203'):
                raise module.GitHubError('Fixture missing base SHA')
            return 'b' * 40
        return 'unchanged'

    module._run_gh = fake
    batch = {'repo': 'a/b', 'cutoff_utc': '2026-10-22T00:00:00+00:00',
        'source_inventory_sha256': 'fixture', 'pr_numbers': [1201, 1202, 1203]}
    recorder = Recorder(); discovery_adapter.install(module, batch, recorder)
    assert module.list_merged_prs is original_list
    result = module.list_merged_prs('a', 'b', limit=100, token='fixture-no-secret')
    assert [r.number for r in result] == [1201]  # Original draft/base-SHA filters still apply.
    assert result[0].body == 'Exact body' and result[0].base_sha == 'b' * 40
    assert result[0].changed_files == ['tests/test_example.py']
    assert [int(a[2]) for a in seen if a[:2] == ['pr', 'view']] == [1201, 1202, 1203]
    assert module._run_gh(['pr', 'diff', '1201']) == 'unchanged'
    quote = json.loads((ROOT / 'openrouter-endpoints.json').read_text())['response']
    reserve = cost_guard.reservation(quote, 2048); assert reserve == Decimal('8.07')
    kwargs = {'model': 'openrouter/anthropic/claude-sonnet-4.6', 'max_tokens': 2048,
        'num_retries': 0, 'messages': [{'role': 'user', 'content': 'fixture'}]}
    response = object(); calls = []

    def completion(**received):
        calls.append(received)
        return response

    with patch.object(cost_guard.urllib.request, 'urlopen', side_effect=lambda *a, **k: io.BytesIO(json.dumps(quote).encode())):
        checked = cost_guard.wrap(Recorder(), completion, Decimal('20'), Decimal('0'))
        assert checked(**kwargs) is response and calls == [kwargs]
        blocked = cost_guard.wrap(Recorder(), completion, Decimal('8'), Decimal('0'))
        try:
            blocked(**kwargs)
        except RuntimeError:
            pass
        else:
            raise AssertionError('Request exceeded reserved campaign allowance')
        assert len(calls) == 1
    quote['data']['endpoints'][0]['pricing']['unknown_paid_tool'] = '1'
    try:
        cost_guard.reservation(quote, 2048)
    except AssertionError:
        pass
    else:
        raise AssertionError('Unknown pricing not rejected')
    total_ids = 0
    for selected in json.loads((BASE / 'cohort.json').read_text()):
        files = build(selected, Decimal('94.024714'))
        config = json.loads(files['native-configs/' + selected['slug'] + '.json'])
        original = json.loads((BASE / 'native-configs' / (selected['slug'] + '.json')).read_text())
        original['pipeline']['options'] = {'limit': 100}
        original['output']['dataset_name'] = 'biotasks28-history-wide'
        assert config == original
        assert files['observed_cli.py'] == (BASE / 'observed_cli.py').read_bytes()
        total_ids += len(json.loads(files['history-identities.json'])['pr_numbers'])
    assert total_ids == 23285
    print('Offline integration passed: native list/draft/base filters, beyond-1000 identities, unchanged descriptors/forwarding, actual-budget reservation boundaries, unknown-price fail-closed and all ten payloads. Zero model/API/job calls.')


if __name__ == '__main__':
    main()
