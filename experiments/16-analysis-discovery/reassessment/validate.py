"""Validate source preservation, complete evidence accounting and format behavior."""
from collections import Counter
import csv
import json
from pathlib import Path

from reconcile import BASE, ROOT, merge, NOTEBOOK_FORMATS, read_rows
from scan import signature


def main():
    summary = json.loads((ROOT/'summary.json').read_text())
    original = json.loads((BASE/'repo-notebook-audit/inventory.json').read_text())
    rows = {r['source_id']: r for r in summary['rows']}
    documents = {d['document_key']: d for d in read_rows(ROOT/'documents.jsonl')}
    assert len(rows) == 1014 and set(rows) == {r['source_id'] for r in original}
    for old in original:
        current = rows[old['source_id']]
        assert all(current[k] == old[k] for k in ('primary_domain', 'repo', 'revision', 'rankings'))
        assert current['notebook_count'] == len(set(current['document_keys']))
        assert current['main_repository_count'] + current['linked_or_package_count'] == current['notebook_count']
        assert sum(current['format_counts'].values()) == current['notebook_count']
        assert all(key in documents for key in current['document_keys'])
        assert current['evidence']['routes']
        assert current['evidence']['project_search_complete'] is False
    counted = {k: d for k, d in documents.items() if d['format'] in NOTEBOOK_FORMATS}
    assert len(counted) == summary['notebooks']['total']
    assert set(counted) == {key for r in rows.values() for key in r['document_keys']}
    assert dict(Counter(d['format'] for d in counted.values())) == summary['notebooks']['format_counts']
    assert summary['notebooks']['across_repositories'] + summary['notebooks']['package_archive_or_download'] == len(counted)
    assert sum(r['notebook_count'] for r in summary['repositories']) == summary['notebooks']['across_repositories']
    with (ROOT/'repository-counts.csv').open() as f:
        assert sum(int(r['notebook_count']) for r in csv.DictReader(f)) == summary['notebooks']['across_repositories']
    # The old displayed five examples must not have truncated the notebook corpus.
    represented = {v['url'] for d in documents.values() for v in d['representations']}
    for record in read_rows(BASE/'repo-notebook-audit/observations.jsonl'):
        for notebook in record['notebooks']:
            assert f"https://github.com/{record['repo']}/blob/{record['revision']}/{notebook['path']}" in represented
    for sid in ['github:scverse/scvi-tools', 'github:scverse/squidpy', 'github:scverse/liana', 'github:scverse/decoupler', 'github:mdanalysis/mdanalysis']:
        assert rows[sid]['result'] == 'located' and rows[sid]['notebook_count'] > 0
    original_probes = json.loads((BASE/'discovery-gap-audit/evidence.json').read_text())
    for finding in original_probes['findings']:
        represented_for_source = {v['url'] for d in rows[finding['source_id']]['documents'] for v in d['representations']}
        for child in finding['submodules']:
            for notebook in child['ipynb_paths']:
                assert f"https://github.com/{child['repository']}/blob/{child['revision']}/{notebook['path']}" in represented_for_source
    sccoord = next(r for r in rows.values() if r['name'] == 'sccoord')
    assert not any('pytorch' in d['url'].lower() for d in sccoord['documents'])
    # Detect literate formats without converting ordinary code blocks to notebooks.
    assert signature('```{code-cell} python\nprint(1)\n```') == 'MyST notebook'
    assert signature('```python\nprint(1)\n```') is None
    assert signature('# %%\nx=1\n# %% [markdown]\n# Analysis') == 'Percent-cell notebook'
    assert signature('### A Pluto.jl notebook ###') == 'Pluto'
    # All-format, version and representation regression examples.
    def doc(path, revision='a'*40, kind='R Markdown'):
        return {'path': path, 'url': f'https://github.com/owner/repo/blob/{revision}/{path}', 'format': kind}
    assert len(merge([doc('analysis.Rmd'), doc('analysis.Rmd', 'b'*40)])) == 1
    assert len(merge([doc('analysis.Rmd'), doc('analysis.qmd', kind='Quarto')])) == 2
    vignette = 'https://bioconductor.org/packages/3.23/bioc/vignettes/pkg/inst/doc/guide'
    paired = merge([{'url': vignette+'.html', 'path': 'guide.html', 'format': 'Rendered vignette'}, {'url': vignette+'.Rmd', 'path': 'guide.Rmd', 'format': 'R Markdown'}, {'url': vignette+'.R', 'path': 'guide.R', 'format': 'Vignette R script'}])
    assert len(paired) == 1 and paired[0]['format'] == 'R Markdown' and len(paired[0]['representations']) == 3
    assert len(merge([doc('a.Rmd'), doc('b.Rmd')], {'github:owner/repo:b.Rmd': 'github:owner/repo:a.Rmd'})) == 1
    assert sum(summary['all'][k] for k in ('located', 'lead', 'none_detected', 'unknown')) == 1014
    checks = {'source_identities_and_domains_preserved': True, 'all_original_detected_paths_retained': True, 'all_format_counts_reconciled': True, 'repository_csv_reconciled': True, 'same_path_versions_and_verified_aliases_deduplicated': True, 'paired_vignette_representations_count_once': True, 'ordinary_code_blocks_not_promoted_to_notebooks': True, 'submodule_and_known_candidate_regressions': True, 'dependency_docs_exclusion': True, 'source_count': len(rows), 'notebook_counts': summary['notebooks'], 'analyses_executed': 0}
    (ROOT/'validation.json').write_text(json.dumps(checks, indent=2) + '\n')
    print(json.dumps(checks))


if __name__ == '__main__':
    main()
