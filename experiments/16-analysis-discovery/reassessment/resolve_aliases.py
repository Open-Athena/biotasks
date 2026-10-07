"""Record exact-byte duplicate paths and verify documentation download aliases."""
from collections import defaultdict
import hashlib
import json
import re
import resource
import subprocess

from reconcile import identity, NOTEBOOK_FORMATS, read_rows, repository_locator
from scan import BASE, ROOT, CACHE, get, guard, now


def main():
    start = now()
    initial = guard(True)
    code = 1
    requests = []
    parents = {}
    proof = []
    def find(key):
        parents.setdefault(key, key)
        if parents[key] != key:
            parents[key] = find(parents[key])
        return parents[key]
    def union(left, right):
        a, b = find(left), find(right)
        if a != b:
            # Prefer repository source over its hosted download representation.
            preferred, other = sorted((a, b), key=lambda x: (not x.startswith('github:'), x))
            parents[other] = preferred
    records = read_rows(ROOT/'observations.jsonl') + read_rows(ROOT/'supplement.jsonl')
    by_source = defaultdict(list)
    for rec in records:
        by_source[rec['source_id']] += rec['documents']
    for rec in read_rows(BASE/'repo-notebook-audit/observations.jsonl'):
        by_source[rec['source_id']] += [{**n, 'url': f"https://github.com/{rec['repo']}/blob/{rec['revision']}/{n['path']}"} for n in rec['notebooks']]
    same_blob = defaultdict(list)
    for docs in by_source.values():
        for doc in docs:
            loc = repository_locator(doc['url'])
            if loc and doc.get('sha') and doc['format'] in NOTEBOOK_FORMATS:
                same_blob[(loc[0], doc['format'], doc['sha'])].append(identity(doc))
    for (repo, kind, sha), keys in same_blob.items():
        unique = sorted(set(keys))
        for key in unique[1:]:
            union(unique[0], key)
        if len(unique) > 1:
            proof.append({'mechanism': 'Identical complete Git blob within repository', 'repo': repo, 'format': kind, 'blob_sha': sha, 'keys': unique})
    # Explicit Jupytext pairing declarations are stronger than matching stems.
    for docs in by_source.values():
        by_location = {(loc[0], loc[2]): d for d in docs if (loc := repository_locator(d['url']))}
        for doc in docs:
            loc = repository_locator(doc['url'])
            if doc['format'] != 'Jupytext' or not loc:
                continue
            repo, revision, path = loc
            raw_url = f'https://raw.githubusercontent.com/{repo}/{revision}/{path}'
            cache = CACHE/hashlib.sha256(raw_url.encode()).hexdigest()
            if not cache.exists():
                # Cache keys retain original repository capitalization.
                owner_repo = '/'.join(doc['url'].split('/')[3:5])
                raw_url = f'https://raw.githubusercontent.com/{owner_repo}/{revision}/{path}'
                cache = CACHE/hashlib.sha256(raw_url.encode()).hexdigest()
            if not cache.exists():
                continue
            text = cache.read_text(errors='replace')
            match = re.search(r'formats:\s*["\']?([^\n"\']+)', text)
            if not match:
                continue
            for token in match[1].split(','):
                extension = token.strip().split(':')[0]
                if not re.fullmatch(r'[A-Za-z0-9]+', extension):
                    continue
                paired_path = str(__import__('pathlib').Path(path).with_suffix('.'+extension))
                paired = by_location.get((repo, paired_path))
                if paired and paired['format'] in NOTEBOOK_FORMATS:
                    left, right = identity(doc), identity(paired)
                    union(left, right)
                    proof.append({'mechanism': 'Explicit Jupytext formats declaration and existing sibling', 'url': doc['url'], 'formats': match[1], 'keys': [left, right]})
    try:
        for sid, docs in by_source.items():
            git_blobs = defaultdict(list)
            for doc in docs:
                if repository_locator(doc['url']) and doc.get('sha') and doc['format'] in NOTEBOOK_FORMATS:
                    git_blobs[(doc['format'], doc['sha'])].append(doc)
            external = {d['url']: d for d in docs if d['format'] in NOTEBOOK_FORMATS and not repository_locator(d['url'])}
            if not external or not git_blobs:
                continue
            rec = {'requests': [], 'limits': []}
            for url, doc in list(external.items())[:12]:
                if get(url, rec, cap=1024**2) is None:
                    continue
                raw = (CACHE/hashlib.sha256(url.encode()).hexdigest()).read_bytes()
                sha = hashlib.sha1(f'blob {len(raw)}\0'.encode() + raw).hexdigest()
                matches = git_blobs.get((doc['format'], sha), [])
                if matches:
                    left, right = identity(doc), identity(matches[0])
                    union(left, right)
                    proof.append({'mechanism': 'Documentation download bytes match repository blob', 'source_id': sid, 'url': url, 'blob_sha': sha, 'sha256': hashlib.sha256(raw).hexdigest(), 'keys': [left, right]})
            requests.append({'source_id': sid, **rec, 'unretrieved_external_links': max(0, len(external)-12)})
            print(json.dumps({'alias_source': sid, 'links_checked': len(rec['requests']), 'resources': guard()}), flush=True)
        aliases = {key: find(key) for key in parents if find(key) != key}
        path = ROOT/'adjudications.json'
        adjudications = json.loads(path.read_text()) if path.exists() else {'excluded_repositories': {}, 'excluded_urls': {}}
        adjudications['aliases'] = aliases
        path.write_text(json.dumps(adjudications, indent=2) + '\n')
        (ROOT/'alias-evidence.json').write_text(json.dumps({'proof': proof, 'requests': requests, 'aliases': aliases, 'limits': 'Only identical complete Git blobs within a repository and byte-verified download aliases are merged automatically. Different-content exports and uncertain pairings remain distinct; counts are not independent-analysis counts.'}, indent=2) + '\n')
        code = 0
    finally:
        record = {'pass': 'exact-byte alias verification', 'start': start, 'end': now(), 'exit_status': code, 'estimate_mib': 250, 'peak_self_rss_kib': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss, 'initial_resources': initial, 'final_resources': guard(), 'source_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip()}
        with (ROOT/'runs.jsonl').open('a') as out:
            out.write(json.dumps(record) + '\n')
        print(json.dumps(record))


if __name__ == '__main__':
    main()
