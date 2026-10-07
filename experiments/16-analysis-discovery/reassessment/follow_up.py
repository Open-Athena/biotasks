"""Repair redirect-relative traversal and reconcile previously selected sources."""
from collections import defaultdict
import json
from pathlib import Path
import resource
import subprocess

from scan import BASE, ROOT, api, follow_documentation, fmt, guard, now, repo_from


def blank(sid, name, repo):
    return {'source_id': sid, 'name': name, 'repo': repo, 'started_at': now(), 'requests': [], 'routes': [], 'trees': [], 'documents': [], 'submodules': [], 'declarations': [], 'collection_links': [], 'rejected_or_unresolved_links': [], 'tutorial_leads': [], 'limits': []}


def main():
    initial = guard(True)
    start = now()
    execution_commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip()
    code = 1
    count = 0
    inventory = json.loads((BASE/'repo-notebook-audit/inventory.json').read_text())
    by_repo = {(r['repo'] or '').lower(): r for r in inventory if r['repo']}
    by_id = {r['source_id']: r for r in inventory}
    observations = {r['source_id']: r for r in (json.loads(l) for l in (ROOT/'observations.jsonl').read_text().splitlines())}
    assert len(observations) == 1014
    candidates = json.loads((BASE/'candidates.json').read_text())
    known_collections = {'mdanalysis/userguide': 'github:mdanalysis/mdanalysis'}
    linked = defaultdict(list)
    candidate_ledger = []
    for candidate in candidates:
        target = repo_from(candidate['canonical_url'])
        sid = None
        if target:
            repo, ref = target
            if repo.lower() in by_repo:
                sid = by_repo[repo.lower()]['source_id']
            elif repo.lower() in known_collections:
                sid = known_collections[repo.lower()]
            elif repo.lower().startswith('danforthcenter/plantcv-tutorial-'):
                sid = 'github:danforthcenter/plantcv'
        if sid and sid in by_id and fmt(candidate['canonical_url']):
            linked[sid].append(candidate)
            status = 'explicit_project_relationship'
        else:
            status = 'no_notebook_locator_or_no_established_inventory_relationship'
        candidate_ledger.append({'candidate_id': candidate['id'], 'source_id': sid, 'status': status, 'url': candidate['canonical_url']})
    (ROOT/'candidate-reconciliation.json').write_text(json.dumps(candidate_ledger, indent=2) + '\n')
    path = ROOT/'supplement.jsonl'
    done = {json.loads(l)['source_id'] for l in path.read_text().splitlines()} if path.exists() else set()
    try:
        with path.open('a') as out:
            for sid, old in observations.items():
                if sid in done:
                    continue
                redirects = [(r['final_url'], 'documentation', r['url']) for r in old['requests'] if r.get('final_url') and r['final_url'].rstrip('/') != r['url'].rstrip('/') and any(x['route'] == 'declared_documentation' and x.get('target') == r['url'] for x in old['routes'])]
                if not redirects and sid not in linked:
                    continue
                rec = blank(sid, old['name'], old['repo'])
                if redirects:
                    follow_documentation(redirects, old['repo'], rec)
                    rec['routes'].append({'route': 'redirect_base_repair', 'status': 'attempted', 'seeds': redirects})
                for candidate in linked[sid]:
                    url = candidate['canonical_url']
                    repo, ref = repo_from(url)
                    # Preserve old pinned source; resolve floating references now,
                    # explicitly not claiming equivalence to the earlier review.
                    if len(ref) != 40:
                        resolved = api(f'repos/{repo}/commits/{ref}', rec)
                        if resolved:
                            url = url.replace('/blob/' + ref + '/', '/blob/' + resolved['sha'] + '/')
                        else:
                            rec['limits'].append('unresolved candidate revision: ' + candidate['id'])
                    rec['documents'].append({'url': url, 'path': url.split('/blob/', 1)[1].split('/', 1)[1], 'format': fmt(url), 'detection': 'Previously selected document ' + candidate['id'] + '; explicit main-repo or official tutorial-collection relationship', 'historical_review_url': candidate['canonical_url'], 'candidate_id': candidate['id']})
                rec['request_errors'] = sum('error' in r for r in rec['requests'])
                rec['finished_at'] = now()
                out.write(json.dumps(rec) + '\n')
                out.flush()
                count += 1
                print(json.dumps({'followup_source': rec['name'], 'documents': len(rec['documents']), 'requests': len(rec['requests']), 'resources': guard()}), flush=True)
        code = 0
    finally:
        record = {'pass': 'redirect repair and candidate reconciliation', 'start': start, 'end': now(), 'exit_status': code, 'completed': count, 'estimate_mib': 250, 'peak_self_rss_kib': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss, 'peak_child_rss_kib': resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss, 'initial_resources': initial, 'final_resources': guard(), 'source_commit': execution_commit}
        with (ROOT/'runs.jsonl').open('a') as out:
            out.write(json.dumps(record) + '\n')
        print(json.dumps(record))


if __name__ == '__main__':
    main()
