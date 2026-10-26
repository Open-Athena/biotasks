import json
import sys
import types
from pathlib import Path

import pytest

from biotasks.generation import resources


def load(name):
    module = types.ModuleType(name)
    exec(compile(resources.assets()[name + '.py'], name, 'exec'), module.__dict__)
    return module


def snapshot(count=205):
    return {'kind': 'history-identities-v1', 'repo': 'test/repo', 'limit': 100,
            'source_inventory_sha256': 'a' * 64, 'cutoff_utc': '2026-10-17T23:59:59+00:00',
            'candidates': [{'number': n, 'state': 'MERGED', 'head_sha': 'b' * 40}
                           for n in range(count, 0, -1)]}


def test_inventory_is_not_a_hundred_pr_cap():
    policy = load('history_policy')
    assert len(policy.validate(snapshot())) == 205
    bad = snapshot(); bad['candidates'].append(bad['candidates'][0])
    with pytest.raises(AssertionError): policy.validate(bad)


def test_abort_preserves_unentered_backlog_without_retrying_entered():
    policy = load('history_policy')
    pending = list(range(205, 0, -1)); chosen = pending[:100]
    returned = chosen[:-1]
    rest, omitted = policy.advance(pending, chosen, returned, chosen[:3])
    assert omitted == [chosen[-1]]
    assert rest[:97] == chosen[3:-1] + [105]
    assert len(rest) == 201
    with pytest.raises(AssertionError): policy.advance(pending, chosen, returned, [999])


def test_real_history_transport_reads_all_three_batches(monkeypatch, tmp_path):
    policy, transport = load('history_policy'), load('history_discovery')
    rows = snapshot()['candidates']; fetched = []
    def run(args, token=None):
        assert args[:2] == ['pr', 'view']
        n = int(args[2]); fetched.append(n)
        return json.dumps({'number': n, 'state': 'MERGED', 'mergedAt': '2026-01-01T00:00:00Z'})
    github = types.SimpleNamespace(_run_gh=run)
    class Recorder:
        def event(self, *a, **kw): pass
        def save(self, name, value, compressed=False):
            (tmp_path / name.removesuffix('.gz')).write_text(json.dumps(value))
    pending = [r['number'] for r in rows]; batches = 0
    while pending:
        chosen = pending[:100]
        batch = {k: snapshot()[k] for k in ('repo', 'cutoff_utc', 'source_inventory_sha256')}
        batch['pr_numbers'] = chosen
        transport.install(github, batch, Recorder())
        returned = json.loads(github._run_gh(['pr', 'list', '--repo', 'test/repo', '--state', 'merged', '--json', transport.FIELDS]))
        with pytest.raises(AssertionError):
            github._run_gh(['pr', 'list', '--repo', 'test/repo', '--state', 'merged', '--json', transport.FIELDS])
        github._run_gh = run
        pending, omitted = policy.advance(pending, chosen, [r['number'] for r in returned], chosen)
        assert not omitted
        batches += 1
    assert batches == 3 and fetched == list(range(205, 0, -1))
    assert len(list(tmp_path.iterdir())) == 205


def test_history_cli_loop_reuses_cache_and_retains_all_descriptors(monkeypatch, tmp_path):
    from contextlib import nullcontext
    from dataclasses import make_dataclass
    from decimal import Decimal
    policy, transport = load('history_policy'), load('history_discovery')
    monkeypatch.setitem(sys.modules, 'history_policy', policy)
    monkeypatch.setitem(sys.modules, 'history_discovery', transport)
    module = load('history_entry')
    Row = make_dataclass('Row', [('number', int), ('head_sha', str), ('base_sha', str)])
    def command(args, token=None):
        return json.dumps({'number': int(args[2]), 'state': 'MERGED', 'mergedAt': '2026-01-01T00:00:00Z'})
    github = types.SimpleNamespace(_run_gh=command)
    def listing():
        rows = json.loads(github._run_gh(['pr', 'list', '--repo', 'test/repo', '--state', 'merged', '--json', transport.FIELDS]))
        return [Row(r['number'], 'b'*40, 'c'*40) for r in rows]
    github.list_merged_prs = listing
    monkeypatch.setitem(sys.modules, 'repo2rlenv', types.SimpleNamespace(github=github))
    monkeypatch.setitem(sys.modules, 'cost_guard', types.SimpleNamespace())
    monkeypatch.setitem(sys.modules, 'litellm', types.SimpleNamespace(completion=lambda: None))
    monkeypatch.setitem(sys.modules, 'observed_cli', types.SimpleNamespace(install_hooks=lambda r: None))
    monkeypatch.setattr(module, 'Path', lambda p: tmp_path / str(p).removeprefix('/work/'))
    (tmp_path/'model-run-budget.json').write_text('{}')
    (tmp_path/'family.json').write_text('{}')
    monkeypatch.setenv('BIOTASKS_HISTORY_DEADLINE_EPOCH', str(module.time.time()+9000))
    class Recorder:
        root = tmp_path
        cost_unknown = False
        calls = 0
        actual_cost = Decimal(0)
        threshold = Decimal(5)
        def save(self, name, value, compressed=False):
            (self.root/name).write_text(json.dumps(value))
        def event(self, name, **kw):
            with (self.root/'events.jsonl').open('a') as f: f.write(json.dumps({'event':name, **kw})+'\n')
        def billing(self): pass
    recorder = Recorder(); invocations = []; cache = tmp_path/'cache'
    def cli(*args, **kw):
        invocations.append(len(invocations))
        if not cache.exists():
            cache.write_text('original bootstrap')
            recorder.calls += 1
        for row in github.list_merged_prs(): recorder.event('candidate_entered', pr=row.number)
        raise SystemExit(0)
    monkeypatch.setattr(module.runpy, 'run_path', cli)
    monkeypatch.setattr(sys, 'argv', [])
    state = {}
    module.execute(recorder, snapshot(), tmp_path/'config', state, lambda: None,
                   lambda r, original, *args: original, lambda *args: nullcontext())
    ledger=json.loads((tmp_path/'history-batches.json').read_text())
    assert ledger['state']=='complete' and not ledger['backlog_pr_numbers']
    assert len(invocations)==3 and recorder.calls==1
    assert len(json.loads((tmp_path/'history-candidates.json').read_text()))==205
    assert github._run_gh is command and github.list_merged_prs is listing
