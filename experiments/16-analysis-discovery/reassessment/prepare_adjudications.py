"""Preserve reviewed exclusions and canonical repository redirects before counting."""
import hashlib
import json
from urllib.parse import urlsplit

from scan import BASE, ROOT, CACHE


def main():
    path = ROOT/'adjudications.json'
    data = json.loads(path.read_text())
    records = [json.loads(l) for p in (ROOT/'observations.jsonl', ROOT/'supplement.jsonl') for l in p.read_text().splitlines()]
    aliases = {}
    proof = []
    for record in records:
        for link in record['collection_links']:
            if link['repo'].lower() == 'just-the-docs/just-the-docs':
                data['excluded_repositories'].setdefault(record['source_id'], {})[link['repo'].lower()] = 'Documentation theme footer, not project analysis collection'
        for request in record['requests']:
            url = request['url']
            if '/git/trees/' not in url or 'api.github.com/repos/' not in url:
                continue
            cache = CACHE/hashlib.sha256(url.encode()).hexdigest()
            if not cache.exists():
                continue
            response = json.loads(cache.read_bytes())
            canonical = response.get('url', '')
            if '/git/trees/' not in canonical:
                continue
            requested_repo = url.split('/repos/', 1)[1].split('/git/trees/', 1)[0].lower()
            actual_repo = canonical.split('/repos/', 1)[1].split('/git/trees/', 1)[0].lower()
            if actual_repo != requested_repo:
                aliases[requested_repo] = actual_repo
                proof.append({'requested_url': url, 'canonical_tree_url': canonical, 'response_sha256': hashlib.sha256(cache.read_bytes()).hexdigest()})
    data['repository_aliases'] = aliases
    # An official AlphaGenome page links this individual notebook. That does not
    # make all notebooks in Google's general cloud sample repository AlphaGenome.
    data['allowed_repository_paths'] = {'github:google-deepmind/alphagenome': {'googlecloudplatform/vertex-ai-samples': ['notebooks/community/alphagenome/cloudai_alphagenome_vai_quickstart.ipynb']}}
    data['allowed_repository_paths']['github:project-monai/generativemodels'] = {'project-monai/tutorials': ['2d_registration/registration_mednist.ipynb']}
    data['allowed_repository_prefixes'] = {'github:project-monai/monailabel': {'project-monai/tutorials': ['monailabel/']}, 'github:mdanalysis/mdanalysis': {'mdanalysis/userguide': ['doc/source/examples/']}}
    data['excluded_repositories'].setdefault('github:google-deepmind/alphagenome', {})['googlecloudplatform/java-docs-samples'] = 'Generic Java deployment examples, not an AlphaGenome notebook collection'
    data['excluded_lead_hosts'] = {record['source_id']: spec['exclude_url_hosts'] for record in records if (spec := json.loads((BASE/'alternative-source-audit/adjudications.json').read_text()).get(record['name']))}
    path.write_text(json.dumps(data, indent=2) + '\n')
    (ROOT/'repository-alias-evidence.json').write_text(json.dumps(proof, indent=2) + '\n')
    print(json.dumps({'canonical_repository_redirects': aliases, 'excluded_repository_relationships': sum(len(v) for v in data['excluded_repositories'].values()), 'scoped_collections': data['allowed_repository_paths']}))


if __name__ == '__main__':
    main()
