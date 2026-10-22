"""An interrupted request must prevent campaign continuation despite a stale snapshot."""

import io
import json
from pathlib import Path
import tarfile
from tempfile import TemporaryDirectory

from campaign import billing_from_archive

with TemporaryDirectory() as directory:
    path = Path(directory) / 'phase-artifacts.tar.gz'

    def archive(events):
        payloads = {
            'native-observations/billing.json': json.dumps({'actual_cost_usd': '0.12', 'cost_complete': True}),
            'native-observations/events.jsonl': ''.join(json.dumps(e) + '\n' for e in events),
        }
        with tarfile.open(path, 'w:gz') as bundle:
            for name, content in payloads.items():
                data = content.encode();member = tarfile.TarInfo(name);member.size = len(data)
                bundle.addfile(member, io.BytesIO(data))

    events = [{'event': 'model_request', 'call': 1},
              {'event': 'model_charge', 'call': 1, 'actual_cost_usd': '0.12'}]
    archive(events)
    result = billing_from_archive(path)
    assert result['cost_complete'] and result['dispatched_calls'] == 1
    archive([*events, {'event': 'model_request', 'call': 2}])
    result = billing_from_archive(path)
    assert not result['cost_complete'] and result['unresolved_calls'] == [2]
    archive([{'event': 'model_request', 'call': 1},
             {'event': 'model_charge', 'call': 1, 'actual_cost_usd': '0.11'}])
    assert not billing_from_archive(path)['cost_complete']
    try:
        billing_from_archive(path, max_uncompressed_bytes=1)
        raise AssertionError('Small metadata scan must enforce its expansion bound')
    except AssertionError as error:
        assert str(error) != 'Small metadata scan must enforce its expansion bound'
print('Campaign billing fixtures passed: complete charges accepted; interrupted and inconsistent ledgers stop advancement.')
