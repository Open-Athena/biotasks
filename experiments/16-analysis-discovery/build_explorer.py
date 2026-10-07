"""Validate the frozen manifest and deterministically build an offline explorer.

Only standard-library metadata work. Does not fetch or execute source analyses.
Run: python3 experiments/16-analysis-discovery/build_explorer.py
"""
import csv
import hashlib
import io
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DOMAINS = ['genomics', 'transcriptomics', 'epigenomics', 'proteomics',
           'structural biology', 'metabolomics', 'systems biology', 'ecology/evolution',
           'RNA biology', 'cellular phenotyping', 'plant biology', 'neuroscience', 'immunology']
STATUSES = {'apparently_suitable', 'excluded', 'unresolved', 'not_reviewed'}


def summarize(rows):
    reviewed = [r for r in rows if r['review_stage'] == 'static_inspection']
    suitable = [r for r in rows if r['assessment'] == 'apparently_suitable']
    coverage = {d: {'identified': sum(d in r['subdomains'] for r in rows),
                    'reviewed': sum(d in r['subdomains'] for r in reviewed),
                    'apparently_suitable': sum(d in r['subdomains'] for r in suitable)}
                for d in DOMAINS}
    return {'identified': len(rows), 'reviewed': len(reviewed),
            'review_stages': dict(Counter(r['review_stage'] for r in rows)),
            'unique': len({r['canonical_url'] for r in rows}),
            'statuses': dict(Counter(r['assessment'] for r in rows)),
            'coverage': coverage,
            'suitable_breadth_original8': sum(coverage[d]['apparently_suitable'] > 0 for d in DOMAINS[:8]),
            'suitable_breadth_revised10': sum(coverage[d]['apparently_suitable'] > 0 for d in DOMAINS[:10]),
            'suitable_breadth_expanded13': sum(coverage[d]['apparently_suitable'] > 0 for d in DOMAINS),
            'dominant_suitable_subdomain_share': max((v['apparently_suitable'] for v in coverage.values()), default=0) / len(suitable) if suitable else None,
            'workflow_labels_suitable': len({r['workflow'] for r in suitable}),
            'workflows_by_subdomain': {d: sorted({r['workflow'] for r in suitable if d in r['subdomains']}) for d in DOMAINS},
            'study_clusters': dict(Counter(r['study_cluster'] for r in rows))}


def build():
    rows = json.loads((ROOT / 'candidates.json').read_text())
    stage_corrections = json.loads((ROOT/'evidence/legacy-review-stages.json').read_text())
    required = {'id', 'route', 'cohort', 'title', 'canonical_url', 'aliases', 'subdomains',
                'workflow', 'language', 'format', 'hosting', 'discovery_index', 'lineage',
                'input_evidence', 'dependencies', 'assessment', 'assessment_reason',
                'code_terms', 'data_terms', 'study_cluster', 'executed', 'evidence'}
    identities = {}; ids = set()
    for r in rows:
        r.setdefault('review_stage', stage_corrections.get(r['id'], 'static_inspection'))
        assert required <= r.keys(), (r['id'], required - r.keys())
        assert r['id'] not in ids; ids.add(r['id'])
        assert r['assessment'] in STATUSES and r['executed'] is False
        assert r['review_stage'] in {'static_inspection', 'access_only', 'identified'}
        assert r['assessment'] != 'apparently_suitable' or r['review_stage'] == 'static_inspection'
        assert set(r['subdomains']) <= set(DOMAINS)
        for url in [r['canonical_url'], *r['aliases']]:
            assert url.startswith(('https://', 'http://'))
            assert url not in identities or identities[url] == r['id'], (url, r['id'])
            identities[url] = r['id']
        for path in r['evidence']: assert (ROOT / path).is_file(), path
    for name in ['github-documents.json', 'kaggle-documents.json']:
        evidence = {x['id']: x for x in json.loads((ROOT/'evidence'/name).read_text())}
        for r in rows:
            if r['id'] in evidence:
                e = evidence[r['id']]
                assert r['source_sha256'] == e.get('source_sha256', e['sha256']), r['id']
    acquisitions = {}
    for name in ['expansion-documents.json', 'catalog-documents.json', 'embedded-documents.json', 'resolution-documents.json']:
        for e in json.loads((ROOT/'evidence'/name).read_text()): acquisitions[e['id']] = e
    for r in rows:
        if r['id'] in acquisitions and r.get('source_sha256'):
            assert r['source_sha256'] == acquisitions[r['id']]['source_sha256'], r['id']
    groups = {}
    for r in rows: groups.setdefault(r['route'] + ' / ' + r['cohort'], []).append(r)
    main = [r for r in rows if r['cohort'] in ['initial', 'competition_first']]
    main_routes = sorted({r['route'] for r in main})
    marginal = {}
    for route in main_routes:
        own = {d for r in main if r['route'] == route and r['assessment'] == 'apparently_suitable' for d in r['subdomains']}
        other = {d for r in main if r['route'] != route and r['assessment'] == 'apparently_suitable' for d in r['subdomains']}
        marginal[route] = sorted(own - other)
    summary = {'stage': 'discovery and static inspection', 'review_state': 'provisional; awaiting user satisfaction',
               'routes': {route: summarize([r for r in rows if r['route'] == route]) for route in sorted({r['route'] for r in rows})},
               'all': summarize(rows), 'main_comparison': summarize(main),
               'groups': {k: summarize(v) for k,v in sorted(groups.items())},
               'main_route_unique_subdomains_suitable': marginal,
               'notes': 'Multilabel counts; purposive sample. Suitability is not execution, scientific validation, or reuse permission.'}
    (ROOT/'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    columns = ['id','title','route','cohort','review_stage','assessment','subdomains','workflow','lineage','canonical_url','input_evidence','dependencies','assessment_reason','code_terms','data_terms','study_cluster']
    out = io.StringIO(newline=''); writer=csv.DictWriter(out, fieldnames=columns, lineterminator='\n'); writer.writeheader()
    for r in rows: writer.writerow({k: '; '.join(r[k]) if isinstance(r[k],list) else r[k] for k in columns})
    (ROOT/'candidates.csv').write_text(out.getvalue())
    payload = json.dumps({'rows': rows, 'summary': summary, 'domains': DOMAINS,
                          'awesome': json.loads((ROOT/'evidence/awesome-biology.json').read_text())}, ensure_ascii=False).replace('<','\\u003c')
    page = (ROOT/'explorer.template.html').read_text().replace('__PAYLOAD__', payload)
    assert '__PAYLOAD__' not in page
    (ROOT/'explorer.html').write_text(page)
    inputs = ['candidates.json', 'protocol.md', 'logbook.md', 'explorer.template.html', 'build_explorer.py']
    inputs += ['expansion.md', 'resolution.md', 'selected-expansion.json', 'selected-catalog.json', 'selected-embedded.json', 'selected-resolution.json', 'inspect_expansion.py', 'resolve_trees.py']
    inputs += [str(p.relative_to(ROOT)) for p in sorted((ROOT/'evidence').glob('*')) if p.is_file()]
    (ROOT/'manifest-sha256.json').write_text(json.dumps({p: hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in inputs}, indent=2)+'\n')
    print(json.dumps({'rows':len(rows),'main':summary['main_comparison']['statuses'], 'all':summary['all']['statuses'], 'marginal':marginal}))


if __name__ == '__main__': build()
