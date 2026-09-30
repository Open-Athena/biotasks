import datetime
import json
import os
from pathlib import Path
import re
import subprocess
import urllib.error
import urllib.request

ROOT = Path('/tmp/bio-discovery-20260929')
DEST = ROOT / 'adoption'
DEST.mkdir(exist_ok=True)
INVENTORY = Path('/home/exedev/.codex/worktrees/ec20/marin/docs/experiments/bio-repository-inventory.json')


def resources(start=False):
    mem = int(next(x.split()[1] for x in Path('/proc/meminfo').read_text().splitlines() if x.startswith('MemAvailable:'))) * 1024
    load = os.getloadavg()[0]
    if start:
        assert mem >= 2.5 * 1024**3 and mem - 100 * 1024**2 >= 2 * 1024**3 and load < 1.5, (mem, load)
    elif mem < 2 * 1024**3 or load > 2.5:
        raise RuntimeError(f'Node resource threshold: {mem=}, {load=}')


def get_json(url, path):
    if path.exists():
        return json.loads(path.read_text())
    resources()
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'biology-adoption-research/1.0'})
        with urllib.request.urlopen(req, timeout=20) as response:
            payload = response.read(10 * 1024**2 + 1)
        assert len(payload) <= 10 * 1024**2, url
        data = json.loads(payload)
    except urllib.error.HTTPError as exc:
        if exc.code not in (404, 429):
            raise
        data = {'error_status': exc.code, 'url': url, 'observed_at': datetime.datetime.now(datetime.UTC).isoformat()}
    path.write_text(json.dumps(data, indent=2) + '\n')
    return data


resources(start=True)
print('start', datetime.datetime.now(datetime.UTC).isoformat(), 'estimated peak 100 MiB', flush=True)
data = json.loads(INVENTORY.read_text())
bioc = json.loads((ROOT / 'bioconductor-metadata.json').read_text())
github = []
for record in data['candidates']:
    if record.get('github_metadata') or not record.get('bioconductor_package'):
        continue
    meta = bioc[record['bioconductor_package']]
    slugs = list(dict.fromkeys(re.findall(r'https://github.com/([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)', ' '.join(meta.get(k, '') for k in ('URL', 'BugReports')))))
    if not slugs:
        continue
    assert len(slugs) == 1, (record['name'], slugs)
    slug = slugs[0].removesuffix('.git')
    path = DEST / (slug.replace('/', '__') + '.github.json')
    if path.exists():
        result = json.loads(path.read_text())
    else:
        resources()
        result = json.loads(subprocess.check_output(['gh', 'api', f'repos/{slug}'], timeout=20))
        result = {k: result.get(k) for k in ('html_url', 'full_name', 'default_branch', 'archived', 'fork', 'stargazers_count', 'pushed_at', 'license', 'description', 'topics', 'homepage')}
        result['source_url'] = f'https://api.github.com/repos/{slug}'
        result['observed_on'] = '2026-09-29'
        path.write_text(json.dumps(result, indent=2) + '\n')
    github.append({'name': record['name'], 'metadata': result, 'mapping_evidence': {k:meta[k] for k in ('URL', 'BugReports') if meta.get(k)}})
    print('github', record['name'], result['stargazers_count'], flush=True)
(DEST / 'github-mappings.json').write_text(json.dumps(github, indent=2) + '\n')

projects = {
    'pysam': ['pysam'], 'Snakemake': ['snakemake'], 'Biopython': ['biopython'],
    'Scanpy': ['scanpy'], 'MultiQC': ['multiqc'], 'cutadapt': ['cutadapt'],
    'deepTools': ['deeptools'], 'MACS2 / MACS3': ['MACS2', 'MACS3'],
    'pybedtools': ['pybedtools'], 'nf-core/tools': ['nf-core'],
    'ViennaRNA': ['ViennaRNA'], 'HTSeq': ['HTSeq'], 'CheckM': ['checkm-genome'],
    'sourmash': ['sourmash'], 'pyBigWig': ['pyBigWig'], 'pyfaidx': ['pyfaidx'],
    'cyvcf2': ['cyvcf2'], 'DendroPy': ['DendroPy'],
}
mappings = []
stats_rate_limited = False
for name, packages in projects.items():
    for package in packages:
        meta = get_json(f'https://pypi.org/pypi/{package}/json', DEST / f'{package.lower()}.pypi.json')
        if 'error_status' in meta:
            print('metadata unavailable', package, meta, flush=True)
            mappings.append({'name': name, 'package': package, 'metadata_error': meta})
            continue
        info = {k:meta['info'].get(k) for k in ('name', 'version', 'summary', 'home_page', 'project_urls', 'license', 'requires_python')}
        stats_path = DEST / f'{package.lower()}.overall.json'
        if package == 'scanpy' and not stats_path.exists():
            stats_path.write_bytes((ROOT / 'pypi-scanpy-overall.json').read_bytes())
        if stats_rate_limited:
            stats = {'error_status': 429, 'reason': 'stopped further stats requests after rate limit'}
        else:
            stats = get_json(f'https://pypistats.org/api/packages/{package.lower()}/overall?mirrors=false', stats_path)
            stats_rate_limited = stats.get('error_status') == 429
        mappings.append({'name': name, 'package': package, 'metadata': info, 'stats_status': stats.get('error_status', 200)})
        print('pypi', package, info['project_urls'], 'stats', stats.get('error_status', 200), flush=True)
(DEST / 'pypi-mappings.json').write_text(json.dumps(mappings, indent=2) + '\n')
print('end', datetime.datetime.now(datetime.UTC).isoformat(), flush=True)
