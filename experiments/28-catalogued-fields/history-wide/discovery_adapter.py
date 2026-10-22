"""Replace only the native listing transport with a frozen contiguous PR batch."""

import datetime
import json

FIELDS = 'number,title,body,state,mergedAt,baseRefName,headRefOid,isDraft,url,files'


def install(github, batch, recorder):
    original = github._run_gh
    requested = False

    def listing_transport(args, token=None):
        nonlocal requested
        if args[:2] != ['pr', 'list']:
            return original(args, token=token)
        assert not requested, 'Exactly one original listing per native invocation'
        requested = True
        assert args[args.index('--repo') + 1].lower() == batch['repo'].lower()
        assert args[args.index('--state') + 1] == 'merged'
        assert args[args.index('--json') + 1] == FIELDS
        ids = batch['pr_numbers']
        assert len(ids) <= 100 and len(set(ids)) == len(ids)
        recorder.event('history_listing_requested', repo=batch['repo'], pr_numbers=ids,
            source_inventory_sha256=batch['source_inventory_sha256'])
        rows = []
        for number in ids:
            # Same gh descriptor fields as upstream list; native base-SHA fetch remains untouched.
            raw = original(['pr', 'view', str(number), '--repo', batch['repo'], '--json', FIELDS], token=token)
            row = json.loads(raw)
            assert row['number'] == number and row['state'] == 'MERGED'
            assert row['mergedAt'] and datetime.datetime.fromisoformat(row['mergedAt'].replace('Z', '+00:00')) <= datetime.datetime.fromisoformat(batch['cutoff_utc'])
            recorder.save(f'discovery-pr-{number}.json.gz', row, compressed=True)
            rows.append(row)
        recorder.event('history_listing_transport_complete', count=len(rows))
        return json.dumps(rows)

    github._run_gh = listing_transport

