"""Reconcile all discovery routes and count all notebook/literate formats."""
from collections import Counter, defaultdict
import csv
import hashlib
import json
from pathlib import Path
import sys
from urllib.parse import unquote, urlsplit, urlunsplit

ROOT = Path(__file__).resolve().parent
BASE = ROOT.parent
sys.path.insert(0, str(BASE))
from consolidate_documents import AUTHORING, consolidate

NOTEBOOK_FORMATS = AUTHORING | {'MyST notebook', 'Percent-cell notebook', 'R notebook HTML export'}


def read_rows(path):
    with path.open() as f:
        return [json.loads(line) for line in f if line.strip()]


def repository_locator(url):
    p = urlsplit(url)
    parts = unquote(p.path).strip('/').split('/')
    if p.hostname == 'github.com' and len(parts) >= 5 and parts[2] == 'blob':
        return '/'.join(parts[:2]).lower(), parts[3], '/'.join(parts[4:])
    if p.hostname == 'raw.githubusercontent.com' and len(parts) >= 4:
        return '/'.join(parts[:2]).lower(), parts[2], '/'.join(parts[3:])
    return None


def identity(doc):
    """One source location across snapshots; versions remain in representations."""
    if location := repository_locator(doc['url']):
        repo, revision, path = location
        return 'github:' + repo + ':' + path
    url = doc.get('group_url', doc['url'])
    p = urlsplit(url)
    if p.hostname in {'bioconductor.org', 'bioconductor.posit.co'} and '/vignettes/' in p.path and '/inst/doc/' in p.path:
        return 'bioc-vignette:' + str(Path(p.path).with_suffix(''))
    # Archive member paths remain distinct even though the archive URL is shared.
    host = 'bioconductor.org' if p.hostname == 'bioconductor.posit.co' else p.netloc
    normalized = urlunsplit((p.scheme, host, p.path, p.query, ''))
    return 'external:' + normalized + ':' + doc.get('group_path', doc['path'])


def merge(documents, aliases=None):
    aliases = aliases or {}
    groups = {}
    for doc in consolidate(documents):
        key = aliases.get(identity(doc), identity(doc))
        if key not in groups:
            groups[key] = {**doc, 'document_key': key}
        else:
            old = groups[key]
            representations = old['representations'] + doc['representations']
            if (doc['format'] in NOTEBOOK_FORMATS and old['format'] not in NOTEBOOK_FORMATS) or (repository_locator(doc['url']) and not repository_locator(old['url'])):
                groups[key] = {**doc, 'document_key': key}
            groups[key]['representations'] = list({(v['url'], v['path'], v['format']): v for v in representations}.values())
    return list(groups.values())


def main():
    inventory = json.loads((BASE/'repo-notebook-audit/inventory.json').read_text())
    previous = {r['source_id']: r for r in read_rows(BASE/'repo-notebook-audit/observations.jsonl')}
    alternative = {r['source_id']: r for r in json.loads((BASE/'alternative-source-audit/summary.json').read_text())['rows']}
    recovery = {r['source_id']: r for r in read_rows(BASE/'authoring-recovery/final-observations.jsonl')}
    current = {r['source_id']: r for r in read_rows(ROOT/'observations.jsonl')}
    assert set(current) == {r['source_id'] for r in inventory}, 'Finish all source observations before publication'
    supplements = read_rows(ROOT/'supplement.jsonl') if (ROOT/'supplement.jsonl').exists() else []
    adjudications = json.loads((ROOT/'adjudications.json').read_text()) if (ROOT/'adjudications.json').exists() else {'excluded_repositories': {}, 'excluded_urls': {}, 'aliases': {}}
    registry = {}
    rows = []
    changes = []
    repository_sources = defaultdict(set)
    repository_revisions = defaultdict(set)
    for item in inventory:
        sid = item['source_id']
        old = previous.get(sid)
        alt = alternative.get(sid)
        rec = current[sid]
        extras = [s for s in supplements if s['source_id'] == sid]
        docs = []
        if old:
            docs += [{**n, 'repo': old['repo'], 'revision': old['revision'], 'url': f"https://github.com/{old['repo']}/blob/{old['revision']}/{n['path']}"} for n in old['notebooks']]
            prior_status = {'present': 'located', 'unknown': 'unknown', 'none_detected': 'none_detected'}[old['status']]
        else:
            docs += alt['documents']
            prior_status = {'document_located': 'located', 'tutorial_lead': 'lead', 'none_detected': 'none_detected'}[alt['result']]
        if sid in recovery:
            docs += recovery[sid]['documents']
        additions = rec['documents'] + [d for s in supplements if s['source_id'] == sid for d in s.get('documents', [])]
        excluded = []
        for d in additions:
            repo = (repository_locator(d['url']) or ('', '', ''))[0]
            reason = adjudications['excluded_repositories'].get(sid, {}).get(repo) or adjudications['excluded_urls'].get(d['url'])
            if reason:
                excluded.append({'url': d['url'], 'reason': reason})
            else:
                docs.append(d)
        consolidated = merge(docs, adjudications.get('aliases', {}))
        notebooks = [d for d in consolidated if d['format'] in NOTEBOOK_FORMATS]
        fallbacks = [d for d in consolidated if d['format'] == 'Rendered vignette']
        leads = rec['tutorial_leads'] + [d for d in consolidated if d['format'] == 'Worked tutorial lead']
        result = 'located' if notebooks or fallbacks else 'lead' if leads or prior_status == 'lead' else 'unknown' if rec['request_errors'] or prior_status == 'unknown' else 'none_detected'
        # Zero files plus a failed route is unresolved, not negative evidence.
        main_repo = (item['repo'] or '').lower()
        direct = sum(bool(repository_locator(d['url'])) and repository_locator(d['url'])[0] == main_repo for d in notebooks)
        for doc in notebooks + fallbacks:
            key = doc['document_key']
            if key not in registry:
                registry[key] = {**doc, 'source_ids': []}
            global_doc = registry[key]
            if (doc['format'] in NOTEBOOK_FORMATS and global_doc['format'] not in NOTEBOOK_FORMATS) or (repository_locator(doc['url']) and not repository_locator(global_doc['url'])):
                registry[key] = {**doc, 'source_ids': global_doc['source_ids'], 'representations': global_doc['representations']}
                global_doc = registry[key]
            global_doc['source_ids'].append(sid)
            combined = global_doc['representations'] + doc['representations']
            global_doc['representations'] = list({(v['url'], v['path'], v['format']): v for v in combined}.values())
        for tree in rec['trees'] + [t for s in extras for t in s.get('trees', [])]:
            repository_sources[tree['repo'].lower()].add(sid)
            repository_revisions[tree['repo'].lower()].add(tree['revision'])
        if main_repo:
            repository_sources[main_repo].add(sid)
            repository_revisions[main_repo].add(item['revision'])
        row = {**item, 'url': 'https://github.com/' + item['repo'] if item['repo'] else alt['source_url'], 'result': result, 'previous_result': prior_status, 'formats': sorted({d['format'] for d in notebooks + fallbacks}), 'documents': consolidated, 'notebook_count': len(notebooks), 'rendered_fallback_count': len(fallbacks), 'main_repository_count': direct, 'linked_or_package_count': len(notebooks)-direct, 'format_counts': dict(Counter(d['format'] for d in notebooks)), 'document_keys': [d['document_key'] for d in notebooks], 'method': 'Reconciled pinned trees, declared submodules and documentation, package/source recovery and explicit candidate relationships', 'evidence': {'routes': rec['routes'] + [r for s in extras for r in s.get('routes', [])], 'trees': rec['trees'] + [t for s in extras for t in s.get('trees', [])], 'submodules': rec['submodules'], 'collection_links': rec['collection_links'] + [c for s in extras for c in s.get('collection_links', [])], 'limits': rec['limits'] + [v for s in extras for v in s.get('limits', [])], 'request_errors': rec['request_errors'] + sum(s.get('request_errors', 0) for s in extras), 'project_search_complete': False, 'excluded_additions': excluded, 'observation_path': 'reassessment/observations.jsonl'}}
        rows.append(row)
        if result != prior_status:
            changes.append({'source_id': sid, 'name': item['name'], 'before': prior_status, 'after': result, 'notebook_count': len(notebooks), 'formats': row['formats']})
    repository_documents = defaultdict(list)
    for d in registry.values():
        if d['format'] in NOTEBOOK_FORMATS and (loc := repository_locator(d['url'])):
            repository_documents[loc[0]].append(d)
            repository_sources[loc[0]].update(d['source_ids'])
            for representation in d['representations']:
                if rloc := repository_locator(representation['url']):
                    repository_revisions[rloc[0]].add(rloc[1])
    repositories = []
    for repo in sorted(repository_sources):
        ds = repository_documents[repo]
        repositories.append({'repository': repo, 'notebook_count': len(ds), 'formats': dict(Counter(d['format'] for d in ds)), 'source_ids': sorted(repository_sources[repo]), 'revisions': sorted(repository_revisions[repo])})
    counted = [d for d in registry.values() if d['format'] in NOTEBOOK_FORMATS]
    repo_total = sum(r['notebook_count'] for r in repositories)
    def tally(rs):
        return {'sources': len(rs), **{k: sum(r['result'] == k for r in rs) for k in ('located', 'lead', 'none_detected', 'unknown')}}
    summary = {'all': tally(rows), 'notebooks': {'total': len(counted), 'across_repositories': repo_total, 'package_archive_or_download': len(counted)-repo_total, 'rendered_fallbacks': sum(d['format'] == 'Rendered vignette' for d in registry.values()), 'source_attributions': sum(r['notebook_count'] for r in rows), 'format_counts': dict(Counter(d['format'] for d in counted)), 'repositories_with_notebooks': sum(r['notebook_count'] > 0 for r in repositories), 'definition': 'All supported notebook/literate authoring formats. One repository/path across recorded snapshots; versions and known paired representations retained as evidence. Shared collections and verified exact-byte copies count once globally. Rendered-only fallbacks and unconfirmed tutorial leads are separate. Counts describe located source documents, not independent analyses, current-checkout totals or validated biological workflows.'}, 'domains': {d: tally([r for r in rows if r['primary_domain'] == d]) for d in sorted({r['primary_domain'] for r in rows})}, 'formats': sorted({f for r in rows for f in r['formats']}), 'repositories': repositories, 'changes': changes, 'rows': rows, 'protocol': 'reassessment/protocol.md', 'completed_source_ledgers': len(current), 'request_errors': sum(r['evidence']['request_errors'] for r in rows), 'limited_sources': sum(bool(r['evidence']['limits'] or r['evidence']['request_errors']) for r in rows)}
    (ROOT/'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    with (ROOT/'documents.jsonl').open('w') as f:
        for key in sorted(registry):
            f.write(json.dumps(registry[key]) + '\n')
    for filename, records, keys in [('repository-counts.csv', repositories, ['repository', 'notebook_count', 'formats', 'source_ids', 'revisions']), ('source-counts.csv', rows, ['source_id', 'name', 'repo', 'result', 'notebook_count', 'main_repository_count', 'linked_or_package_count', 'rendered_fallback_count', 'format_counts'])]:
        with (ROOT/filename).open('w') as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            for record in records:
                writer.writerow({k: json.dumps(record[k], sort_keys=True) if isinstance(record[k], (list, dict)) else record[k] for k in keys})
    (ROOT/'input-sha256.json').write_text(json.dumps({str(p.relative_to(BASE)): hashlib.sha256(p.read_bytes()).hexdigest() for p in [ROOT/'observations.jsonl', ROOT/'scan.py', ROOT/'reconcile.py', BASE/'consolidate_documents.py', BASE/'repo-notebook-audit/observations.jsonl', BASE/'alternative-source-audit/summary.json', BASE/'authoring-recovery/final-observations.jsonl'] + [p for p in [ROOT/'supplement.jsonl', ROOT/'adjudications.json'] if p.exists()]}, indent=2) + '\n')
    print(json.dumps({k: summary[k] for k in ('all', 'notebooks', 'completed_source_ledgers', 'limited_sources')}))


if __name__ == '__main__':
    main()
