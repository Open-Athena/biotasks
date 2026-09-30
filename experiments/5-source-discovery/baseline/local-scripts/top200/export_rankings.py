import json
from pathlib import Path
old=Path('/tmp/bio-discovery-20260929/top100/export_rankings.py').read_text()
s=old[:old.index('# Provenance describes scope')]
s=s.replace("root=scratch/'top100'","root=scratch/'top200'")
s=s.replace("01-discovery/data');dest.mkdir(exist_ok=True)","01-discovery/data/top200-2026-09-29');dest.mkdir(exist_ok=True)")
s=s.replace("'reason':r.get('exclusion','')", "'reason':decisions['bioconda_exclusions'].get(r['package'],r.get('exclusion',''))")
s=s.replace('heapq.nlargest(150,','heapq.nlargest(250,')
# Additional identity metadata enriches package lists, while star ranking remains frozen.
s=s.replace("unique={r['metadata']['nameWithOwner'].lower():r['metadata'] for r in gh_records['records'] if r['metadata']}","unique={r['metadata']['nameWithOwner'].lower():r['metadata'] for r in json.loads((scratch/'top100/github-source-metadata.json').read_text())['records'] if r['metadata']}")
s+='''
manifest=json.loads((dest.parent/f'ranking-provenance-{stamp}.json').read_text())
manifest['cohort_size']=200
manifest['baseline_provenance_file']=f'../ranking-provenance-{stamp}.json'
manifest['comparison_design']='Extend four rankings from 100 to 200 using the identical numeric snapshots. Preserve all first-100 source IDs, scores and manual labels. Freeze the GitHub ranking universe and its metadata; additional GitHub reads enrich package-source identity and tags only.'
manifest['bioconda']['screened_raw_rows']=500
manifest['bioconductor']['screened_raw_rows']=250
manifest['pypi']['current_pypi_identity_checks']=350
manifest['github']['top200_identity_observed_at']=gh_records['top200_identity_observed_at']
manifest['github']['additional_identity_checks']=len(gh_records['records'])-manifest['github']['requested_names']
manifest['github']['frozen_ranking_universe']=True
for route in d['cohorts']:manifest[route]['cutoff']=d['cohorts'][route][-1]
manifest['source_identity_corrections']['top200_overrides']=json.loads((root/'identity-overrides.json').read_text())
manifest['source_identity_corrections']['top200_notes']={
 'BioPerl':'BioPerl metapackage and BioPerl core resolve to the pinned official 1.7.8 archive; collapse using maximum counter. Other BioPerl extension archives remain distinct.',
 'GMAP, ClustalW, Clustal Omega, Stacks, Subread, RpsbProc':'Use versioned official source distributions from pinned recipes, not generic homepages.',
 'gatk4-spark':'Missing standalone recipe at pinned revision. Spark distribution maps to existing GATK source; it does not contribute a second source.',
 'pyranges and ncls':'Verify GitHub redirects to the already recorded pyranges organization sources before deduplication.',
 'pephubclient':'PyPI description and trusted-publisher provenance identify pepkit/pephubclient; stale homepage databio/pephubclient did not resolve.',
 'fcsparser':'PyPI project_urls point to unrelated eyurtsev/kor. Description example/documentation links identify eyurtsev/fcsparser.',
 'medspacy-quickumls':'Description identifies the maintained medspacy fork rather than its stale upstream homepage.',
 'sccoord':'Current GitHub link did not resolve. Retain current official PyPI source distribution; no repository topics asserted.',
}
manifest['manual_annotation_axes']['primary_domain']+=' Four additional groups are introduced only for newly selected sources: Immunology, Metabolomics, Ecology & conservation, Biomechanics & physiology. Existing source labels are unchanged.'
manifest['tag_mapping_changes']='Extend exact-string mapping to new scientific tags; split immunology and metabolomics out of the old broad general-biology mapping. Both depth cutoffs are recalculated with this same expanded mapping in expansion-results.'
manifest['baseline_artifact_sha256']=json.loads((root/'baseline-hashes.json').read_text())
manifest['additional_current_pypi_metadata']=[{'package':p.stem,'observed_at':q.get('observed_at'),'response_sha256':q.get('response_sha256'),'source_url':q.get('source_url'),'version':q.get('metadata',{}).get('version'),'source_distributions':q.get('source_distributions',[])} for p in sorted((root/'pypi-current').glob('*.json')) if (q:=json.loads(p.read_text()))]
manifest['selected_recipe_evidence']=[{'package':x['package'],'recipe_url':x.get('recipe_url'),'recipe_sha256':x.get('recipe_sha256')} for x in json.loads((root/'bioconda-screen.json').read_text())['records'] if x['package'] in {p for c in d['cohorts']['bioconda'] for p in c['packages']}]
(dest/f'pypi-count-query-{stamp}.sql').write_text((dest.parent/f'pypi-count-query-{stamp}.sql').read_text())
manifest['retained_artifact_sha256']={f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in sorted(dest.glob(f'*-{stamp}.*')) if f.name.startswith(('ranking','source-','tag-domains','pypi-count-query')) and 'results' not in f.name and 'provenance' not in f.name and 'topic-frequencies' not in f.name}
(dest/f'ranking-provenance-{stamp}.json').write_text(json.dumps(manifest,indent=2)+'\\n')
print('Exported',len(rankings),'positions;',len(observations),'unique sources')
'''
exec(compile(s,__file__,'exec'))
