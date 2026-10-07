"""Bounded project-graph discovery; never executes upstream code."""
import configparser
from datetime import datetime, timezone
import hashlib
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import re
import resource
import subprocess
import sys
import time
from urllib.parse import quote, unquote, urljoin, urlsplit, urlunsplit
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent
BASE = ROOT.parent
CACHE = Path('/tmp/biotasks16-reassessment-cache-01a1183d')
CACHE.mkdir(exist_ok=True)
EXT = {'.ipynb': 'Jupyter', '.rmd': 'R Markdown', '.rmarkdown': 'R Markdown', '.qmd': 'Quarto', '.rnw': 'Sweave/knitr', '.rtex': 'Sweave/knitr', '.nb': 'Wolfram notebook', '.mlx': 'MATLAB Live Script', '.livemd': 'Livebook', '.dib': '.NET Interactive', '.rnb.html': 'R notebook HTML export'}
DOC = re.compile(r'tutorial|notebook|vignette|user.?guide|documentation|(?:^|[/_.-])docs?(?:[/_.-]|$)|examples?', re.I)
BAD_HOSTS = {'pypi.org', 'doi.org', 'zenodo.org', 'twitter.com', 'x.com', 'img.shields.io', 'readthedocs.org', 'stackoverflow.com', 'opensource.org', 'anaconda.org', 'badge.fury.io', 'codecov.io'}


def now():
    return datetime.now(timezone.utc).isoformat()


def guard(start=False):
    memory = next(int(x.split()[1]) * 1024 for x in Path('/proc/meminfo').read_text().splitlines() if x.startswith('MemAvailable:'))
    load = os.getloadavg()[0]
    assert memory >= (2.5 if start else 2) * 1024**3 and load < (1.5 if start else 2.5), (memory, load)
    if start:
        assert memory - 250 * 1024**2 >= 2 * 1024**3
    return {'available_bytes': memory, 'load1': load}


def fmt(path):
    return next((v for k, v in EXT.items() if path.lower().endswith(k)), None)


def signature(text):
    if ('import marimo' in text or 'from marimo' in text) and ('marimo.App(' in text or '@app.cell' in text):
        return 'marimo'
    if '### A Pluto.jl notebook ###' in text:
        return 'Pluto'
    if 'jupytext:' in text and ('text_representation:' in text or 'formats:' in text):
        return 'Jupytext'
    if re.search(r'^\s*(```|~~~|:::)\{code-cell\}', text, re.M):
        return 'MyST notebook'
    if len(re.findall(r'^\s*#\s*%%(?:\s|$)', text, re.M)) >= 2:
        return 'Percent-cell notebook'
    return None


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
        self.current = None

    def handle_starttag(self, tag, attrs):
        if tag == 'a':
            self.current = [dict(attrs).get('href', ''), '']

    def handle_data(self, value):
        if self.current is not None:
            self.current[1] += value

    def handle_endtag(self, tag):
        if tag == 'a' and self.current is not None:
            self.links.append(self.current)
            self.current = None


def links(text, base):
    parser = Links()
    parser.feed(text)
    pairs = parser.links + [(m[1], m[0]) for m in re.findall(r'\[([^\]]*)\]\((https?://[^\s)]+)', text)]
    pairs += [(m.group(), text[max(0, m.start()-100):m.start()]) for m in re.finditer(r'https?://[^\s<>"\')\]]+', text)]
    seen = set()
    for href, label in pairs:
        try:
            url = urljoin(base, href).rstrip('.,;`')
            p = urlsplit(url)
        except ValueError:
            continue
        url = urlunsplit((p.scheme, p.netloc, p.path, p.query, ''))
        if p.scheme in {'http', 'https'} and url not in seen:
            seen.add(url)
            yield url, re.sub(r'\s+', ' ', label)[-180:]


def get(url, rec, api=False, cap=1024**2):
    guard()
    if len(rec['requests']) >= 32:
        rec['limits'].append('32-request source budget')
        return None
    event = {'url': url, 'observed_at': now()}
    rec['requests'].append(event)
    key = hashlib.sha256(url.encode()).hexdigest()
    cache = CACHE / key
    try:
        if cache.exists():
            raw = cache.read_bytes()
            event['cache_reused'] = True
            if cache.with_suffix('.meta').exists():
                event.update(json.loads(cache.with_suffix('.meta').read_text()))
        elif api:
            p = subprocess.run(['gh', 'api', url.removeprefix('https://api.github.com/')], capture_output=True, timeout=15)
            if p.returncode:
                message = p.stderr.decode(errors='replace')[:400]
                if 'rate limit' in message.lower():
                    raise RuntimeError('GitHub rate limit: stop and retain checkpoint')
                raise ValueError(message)
            raw = p.stdout
        else:
            with urlopen(Request(url, headers={'User-Agent': 'BioTasks-bounded-discovery/2.0'}), timeout=6) as response:
                raw = response.read(cap + 1)
                event['final_url'] = response.url
        event.update(bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())
        if len(raw) > cap:
            raise ValueError(f'response exceeds {cap}-byte cap')
        if not cache.exists():
            cache.write_bytes(raw)
            cache.with_suffix('.meta').write_text(json.dumps({k: event[k] for k in ('final_url',) if k in event}))
        return json.loads(raw) if api else raw.decode(errors='replace')
    except RuntimeError:
        raise
    except Exception as exc:
        event['error'] = str(exc)[:400]
        return None


def api(endpoint, rec):
    return get('https://api.github.com/' + endpoint, rec, api=True, cap=8*1024**2)


def rawfile(repo, revision, path, rec):
    return get(f'https://raw.githubusercontent.com/{repo}/{revision}/{quote(path)}', rec, cap=128*1024)


def hit(rec, repo, revision, item, kind, mechanism):
    if '.ipynb_checkpoints' in item['path']:
        return
    key = (repo.lower(), revision, item['path'])
    if any((d.get('repo', '').lower(), d.get('revision'), d['path']) == key for d in rec['documents']):
        return
    rec['documents'].append({'repo': repo, 'revision': revision, 'path': item['path'], 'format': kind, 'sha': item.get('sha'), 'url': f"https://github.com/{repo}/blob/{revision}/{item['path']}", 'detection': mechanism})


def repo_from(url):
    p = urlsplit(url)
    if p.hostname == 'colab.research.google.com' and p.path.startswith('/github/'):
        url = 'https://github.com/' + p.path.removeprefix('/github/')
    elif p.hostname == 'nbviewer.org' and p.path.startswith('/github/'):
        url = 'https://github.com/' + p.path.removeprefix('/github/')
    elif p.hostname == 'raw.githubusercontent.com':
        parts = p.path.strip('/').split('/', 3)
        if len(parts) == 4:
            url = f'https://github.com/{parts[0]}/{parts[1]}/blob/{parts[2]}/{parts[3]}'
    p = urlsplit(url)
    parts = unquote(p.path).strip('/').split('/')
    if p.hostname != 'github.com' or len(parts) < 2:
        return None
    repo = '/'.join(parts[:2]).removesuffix('.git')
    ref = parts[3] if len(parts) > 3 and parts[2] in {'blob', 'tree'} else 'HEAD'
    return repo, ref


def inspect_tree(repo, revision, rec, relationship, depth=0):
    if any(t['repo'].lower() == repo.lower() and t['revision'] == revision for t in rec['trees']):
        return []
    data = api(f'repos/{repo}/git/trees/{revision}?recursive=1', rec)
    if data is None:
        rec['routes'].append({'route': relationship, 'target': repo, 'status': 'access_failed'})
        return []
    revision = data['sha']
    tree = data.get('tree', [])
    rec['trees'].append({'repo': repo, 'revision': revision, 'relationship': relationship, 'truncated': data.get('truncated', True), 'entries': len(tree)})
    if data.get('truncated', True):
        rec['limits'].append(f'truncated tree: {repo}')
    files = [x for x in tree if x.get('type') == 'blob']
    for item in files:
        if kind := fmt(item['path']):
            hit(rec, repo, revision, item, kind, relationship + ': filename')
    declarations = [x for x in files if x['path'].lower() in {'readme.md', 'readme.rst', 'readme', 'pyproject.toml', '.readthedocs.yaml', '.readthedocs.yml', 'docs/conf.py', 'doc/conf.py', 'docs/source/conf.py'}]
    declarations.sort(key=lambda x: (not x['path'].lower().startswith('readme'), x['path'] != 'pyproject.toml', x['path']))
    found_links = []
    for item in declarations[:3 if depth == 0 else 1]:
        text = rawfile(repo, revision, item['path'], rec)
        if text:
            rec['declarations'].append({'repo': repo, 'revision': revision, 'path': item['path']})
            found_links += [(url, label, f'{repo}@{revision}/{item["path"]}') for url, label in links(text, f'https://github.com/{repo}/')]
    candidates = [x for x in files if Path(x['path']).suffix.lower() in {'.py', '.jl', '.r', '.md', '.rst'} and DOC.search(x['path']) and not any(t in x['path'].lower().split('/') for t in ('tests', 'test', '_static')) and x not in declarations]
    candidates.sort(key=lambda x: (not re.search(r'notebook|marimo|pluto|tutorial|vignette', x['path'], re.I), x.get('size', 0) > 128*1024, x['path']))
    for item in candidates[:4 if depth == 0 else 2]:
        text = rawfile(repo, revision, item['path'], rec)
        if text:
            if kind := signature(text):
                hit(rec, repo, revision, item, kind, relationship + ': text signature')
            found_links += [(url, label, f'{repo}@{revision}/{item["path"]}') for url, label in links(text, f'https://github.com/{repo}/')]
    rec['routes'].append({'route': 'text_notebook_signatures', 'target': repo, 'status': 'bounded', 'candidate_paths': len(candidates), 'selected_paths': [x['path'] for x in candidates[:4 if depth == 0 else 2]]})
    if len(candidates) > (4 if depth == 0 else 2):
        rec['limits'].append(f'unprobed text candidates: {repo}')
    gitlinks = [x for x in tree if x.get('type') == 'commit']
    if gitlinks:
        text = rawfile(repo, revision, '.gitmodules', rec)
        config = configparser.ConfigParser(interpolation=None)
        if text:
            try:
                config.read_string('\n'.join(line.lstrip() for line in text.splitlines()))
            except configparser.Error:
                rec['limits'].append(f'unparseable gitmodules: {repo}')
        modules = {config[s].get('path'): config[s].get('url', '') for s in config.sections()}
        for item in gitlinks:
            url = modules.get(item['path'], '')
            if url.startswith('../'):
                url = urljoin(f'https://github.com/{repo}/', url)
            if url.startswith('git@github.com:'):
                url = 'https://github.com/' + url.removeprefix('git@github.com:')
            target = repo_from(url.rstrip('/'))
            candidate = bool(DOC.search(item['path'] + ' ' + url))
            edge = {'parent_repo': repo, 'path': item['path'], 'url': url, 'revision': item['sha'], 'status': 'pending' if candidate else 'not_followed_dependency_or_unclassified', 'basis': 'Declared gitmodule; documentation/tutorial path heuristic'}
            rec['submodules'].append(edge)
            if candidate and target and depth < 2:
                inspect_tree(target[0], item['sha'], rec, 'declared tutorial submodule', depth + 1)
                edge['status'] = 'tree_inspected' if any(t['repo'].lower() == target[0].lower() and t['revision'] == item['sha'] for t in rec['trees']) else 'access_failed'
            elif candidate:
                edge['status'] = 'unresolved_host_or_depth_limit'
    else:
        rec['routes'].append({'route': 'submodules', 'target': repo, 'status': 'none_declared_in_tree'})
    return found_links


def follow_documentation(seeds, main_repo, rec):
    queue = []
    collections = []
    main_owner = main_repo.split('/')[0].lower() if main_repo else ''
    def consider(url, label, parent, trusted=False):
        parsed = urlsplit(url)
        if parsed.hostname in BAD_HOSTS or any(x in parsed.path.lower() for x in ('/issues', '/pull/', '/actions', '/badge', '.svg', '.png', '.jpg')):
            return
        target = repo_from(url)
        if target:
            repo, ref = target
            if main_repo and repo.lower() == main_repo.lower():
                return
            own = repo.split('/')[0].lower() == main_owner and bool(main_owner)
            collection = bool(DOC.search(repo.split('/')[1]))
            launch = parsed.hostname in {'colab.research.google.com', 'nbviewer.org'}
            direct_source = bool(fmt(parsed.path)) or bool(re.search(r'edit.*(?:source|page)|download.*(?:notebook|source)', label, re.I))
            if (own and collection) or (trusted and (collection or launch or direct_source)):
                collections.append((repo, ref, url, parent, label))
            elif DOC.search(url + ' ' + label):
                rec['rejected_or_unresolved_links'].append({'url': url, 'parent': parent, 'reason': 'External repository ownership/collection relationship not established'})
            return
        host = parsed.hostname or ''
        declared_doc = bool(DOC.search(label + ' ' + url)) or '.readthedocs.' in host or host.startswith(('docs.', 'documentation.', 'userguide.'))
        token = re.sub(r'[^a-z0-9]', '', main_repo.split('/')[-1].lower()).removesuffix('2') if main_repo else re.sub(r'[^a-z0-9]', '', rec['name'].lower())
        associated = (len(token) >= 4 and token in re.sub(r'[^a-z0-9]', '', url.lower())) or ('pypi.org/pypi/' in parent) or ('bioconda-recipes/' in parent) or parent.startswith('prior ')
        explicit_label = label.strip().lower() in {'documentation', 'docs', 'tutorials', 'user guide', 'online documentation', 'full documentation'}
        same_site = trusted and urlsplit(parent).hostname == host
        if declared_doc and not (associated or explicit_label or same_site):
            rec['rejected_or_unresolved_links'].append({'url': url, 'parent': parent, 'reason': 'Documentation ownership not established; possible dependency link'})
            return
        if declared_doc and not parsed.path.lower().endswith(('.pdf', '.zip', '.gz', '.tar', '.bib', '.css', '.js')):
            if (url, parent) not in queue:
                queue.append((url, parent))
    for url, label, parent in seeds:
        consider(url, label, parent)
    # Prefer specific tutorial indexes over general landing pages.
    queue.sort(key=lambda x: (not re.search(r'tutorial|notebook|examples|userguide', x[0], re.I), x[0]))
    seen = set()
    checked = 0
    while queue and checked < 4:
        url, parent = queue.pop(0)
        if url in seen:
            continue
        seen.add(url)
        checked += 1
        text = get(url, rec)
        rec['routes'].append({'route': 'declared_documentation', 'target': url, 'parent': parent, 'status': 'read' if text is not None else 'access_failed'})
        if text is None:
            continue
        resolved_url = rec['requests'][-1].get('final_url', url)
        page_links = list(links(text, resolved_url))
        for target, label in page_links:
            consider(target, label, resolved_url, trusted=True)
            kind = fmt(urlsplit(target).path)
            if kind and not repo_from(target) and urlsplit(target).hostname == urlsplit(resolved_url).hostname:
                rec['documents'].append({'path': urlsplit(target).path, 'format': kind, 'url': target, 'detection': 'Official documentation download link; target not inspected'})
        if DOC.search(url) and re.search(r'<pre|<code|code-cell', text, re.I):
            rec['tutorial_leads'].append({'url': url, 'detection': 'Documentation code blocks; not counted as authoring notebook'})
        queue.sort(key=lambda x: (urlsplit(x[0]).hostname != urlsplit(url).hostname, not re.search(r'tutorial|notebook|examples', x[0], re.I)))
    if queue:
        rec['limits'].append('documentation page budget (4)')
    if not checked:
        rec['routes'].append({'route': 'declared_documentation', 'status': 'no_eligible_declared_target'})
    selected = []
    for repo, ref, url, parent, label in collections:
        if repo.lower() in {r[0].lower() for r in selected} or any(t['repo'].lower() == repo.lower() for t in rec['trees']):
            continue
        selected.append((repo, ref, url, parent, label))
    for repo, ref, url, parent, label in selected[:2]:
        resolved = api(f'repos/{repo}/commits/{quote(ref, safe="")}', rec)
        rec['collection_links'].append({'repo': repo, 'declared_url': url, 'parent': parent, 'label': label, 'resolved_revision': resolved.get('sha') if resolved else None})
        if resolved:
            inspect_tree(repo, resolved['sha'], rec, 'declared documentation collection', depth=1)
    if len(selected) > 2:
        rec['limits'].append('linked collection budget (2)')


def scan(item, source, old_alt):
    rec = {'source_id': item['source_id'], 'name': item['name'], 'repo': item['repo'], 'revision': item['revision'], 'started_at': now(), 'requests': [], 'routes': [], 'trees': [], 'documents': [], 'submodules': [], 'declarations': [], 'collection_links': [], 'rejected_or_unresolved_links': [], 'tutorial_leads': [], 'limits': []}
    seeds = []
    if item['repo']:
        seeds += inspect_tree(item['repo'], item['revision'], rec, 'pinned main repository')
    else:
        prior = old_alt[item['source_id']]
        rec['routes'].append({'route': 'prior_package_archive_documentation', 'status': 'prior_evidence_retained', 'prior_finished_at': prior.get('finished_at'), 'had_access_or_budget_limit': prior.get('has_access_or_budget_limit')})
        for request in prior.get('requests', []):
            url = request['url']
            if ('error' in request or not prior['documents']) and not any(t in url for t in ('api.github', 'raw.githubusercontent', '.tar.', '.zip', 'files.pythonhosted', 'api.bitbucket', 'gitlab.com/api')) and not any(t in url for t in ('pytorch.org', 'numpy.org')):
                seeds.append((url, 'documentation retry', 'prior request evidence'))
        for lead in prior.get('leads', []):
            seeds.append((lead['url'], lead.get('label', ''), 'prior tutorial lead'))
    # Only labeled metadata fields, not arbitrary package-description dependency links.
    metadata_urls = [u for u in source.get('evidence_urls', []) if 'pypi.org/pypi/' in u or ('raw.githubusercontent.com/bioconda/' in u)]
    for url in metadata_urls[:1]:
        text = get(url, rec)
        if text:
            if 'pypi.org/pypi/' in url:
                try:
                    info = json.loads(text)['info']
                    seeds += [(u, label, url) for label, u in (info.get('project_urls') or {}).items() if u and re.search(r'doc|tutorial|homepage|home page', label, re.I)]
                    if info.get('home_page'):
                        seeds.append((info['home_page'], 'project homepage documentation', url))
                except (ValueError, KeyError):
                    rec['limits'].append('invalid PyPI metadata')
            else:
                seeds += [(u, field, url) for field, u in re.findall(r'^\s*(home|doc_url|dev_url):\s*["\']?(https?://[^\s"\']+)', text, re.M)]
    follow_documentation(seeds, item['repo'], rec)
    rec['limits'] = sorted(set(rec['limits']))
    rec['finished_at'] = now()
    rec['request_errors'] = sum('error' in r for r in rec['requests'])
    rec['project_search_complete'] = False
    return rec


def main():
    started = now()
    initial = guard(True)
    code = 1
    completed = 0
    inventory = json.loads((BASE/'repo-notebook-audit/inventory.json').read_text())
    sources = {s['source_id']: s for s in json.loads((BASE/'repo-notebook-audit/source-observations.json').read_text())}
    old = {r['source_id']: r for r in (json.loads(l) for l in (BASE/'repo-notebook-audit/observations.jsonl').read_text().splitlines())}
    old_alt = {r['source_id']: r for r in (json.loads(l) for l in (BASE/'alternative-source-audit/final-observations.jsonl').read_text().splitlines())}
    path = ROOT/'observations.jsonl'
    done = {json.loads(l)['source_id'] for l in path.read_text().splitlines()} if path.exists() else set()
    inventory.sort(key=lambda r: (not bool(old.get(r['source_id'], {}).get('submodules')), old.get(r['source_id'], {}).get('status') == 'present', r['source_id']))
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else len(inventory)
    try:
        with path.open('a') as out:
            for item in inventory:
                if item['source_id'] in done:
                    continue
                rec = scan(item, sources[item['source_id']], old_alt)
                out.write(json.dumps(rec) + '\n')
                out.flush()
                completed += 1
                print(json.dumps({'completed_this_run': completed, 'completed_total': len(done)+completed, 'source': item['name'], 'documents': len(rec['documents']), 'request_errors': rec['request_errors'], 'resources': guard()}), flush=True)
                if completed >= limit:
                    break
        code = 0
    finally:
        record = {'start': started, 'end': now(), 'exit_status': code, 'completed': completed, 'estimate_mib': 250, 'peak_self_rss_kib': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss, 'peak_child_rss_kib': resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss, 'initial_resources': initial, 'final_resources': guard(), 'source_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip()}
        with (ROOT/'runs.jsonl').open('a') as out:
            out.write(json.dumps(record) + '\n')
        print(json.dumps(record), flush=True)


if __name__ == '__main__':
    main()
