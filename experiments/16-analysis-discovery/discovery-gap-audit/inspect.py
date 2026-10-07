"""Bounded, metadata-only regression probes for the reopened discovery question.

Run with the shared heavy-work lock, thread limits and reduced priority.
Does not execute notebooks, install packages or download biological inputs.
"""

import base64
import configparser
import hashlib
import json
import os
from pathlib import Path
import resource
import subprocess
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parent
PARENT = ROOT.parent
TARGETS = ("scverse/scvi-tools", "scverse/decoupler", "scverse/liana", "scverse/squidpy")


def now():
    return datetime.now(timezone.utc).isoformat()


def guard(start=False):
    available = next(int(line.split()[1]) * 1024 for line in Path('/proc/meminfo').read_text().splitlines() if line.startswith('MemAvailable:'))
    load = os.getloadavg()[0]
    assert available >= (2.5 if start else 2) * 1024**3
    assert load < (1.5 if start else 2.5)
    if start:
        assert available - 100 * 1024**2 >= 2 * 1024**3
    return {'available_bytes': available, 'load1': load}


requests = []


def api(endpoint):
    guard()
    result = subprocess.run(['gh', 'api', endpoint], capture_output=True, timeout=30, check=True)
    assert len(result.stdout) < 8 * 1024**2
    requests.append({'endpoint': endpoint, 'observed_at': now(), 'bytes': len(result.stdout), 'sha256': hashlib.sha256(result.stdout).hexdigest()})
    return json.loads(result.stdout)


def main():
    started = now()
    initial = guard(True)
    rows = [json.loads(line) for line in (PARENT/'repo-notebook-audit/observations.jsonl').open()]
    queue = [{k: r[k] for k in ('source_id', 'repo', 'revision', 'status', 'submodules', 'unprobed_text_files')} for r in rows]
    (ROOT/'reassessment-queue.json').write_text(json.dumps(queue, indent=2) + '\n')
    findings = []
    for repo in TARGETS:
        old = next(r for r in rows if r['repo'] == repo)
        revision = old['revision']
        modules = api(f'repos/{repo}/contents/.gitmodules?ref={revision}')
        module_text = base64.b64decode(modules['content']).decode()
        config = configparser.ConfigParser()
        config.read_string(module_text)
        tree = api(f'repos/{repo}/git/trees/{revision}?recursive=1')
        assert not tree['truncated']
        links = []
        for section in config.sections():
            path = config[section]['path']
            url = config[section]['url']
            assert url.startswith('https://github.com/')
            child_repo = url.removeprefix('https://github.com/').removesuffix('.git')
            gitlink = next(x for x in tree['tree'] if x['path'] == path and x['type'] == 'commit')
            child_revision = gitlink['sha']
            child = api(f'repos/{child_repo}/git/trees/{child_revision}?recursive=1')
            assert not child['truncated']
            notebooks = [x for x in child['tree'] if x['type'] == 'blob' and x['path'].endswith('.ipynb') and '.ipynb_checkpoints' not in x['path']]
            links.append({'path': path, 'repository': child_repo, 'revision': child_revision, 'ipynb_paths': notebooks, 'nested_submodules': [x for x in child['tree'] if x['type'] == 'commit']})
        findings.append({'source_id': old['source_id'], 'repo': repo, 'parent_revision': revision, 'previous_status': old['status'], 'gitmodules': module_text, 'submodules': links})
        print(repo, [(x['repository'], len(x['ipynb_paths'])) for x in links], flush=True)
    scvi = findings[0]['submodules'][0]
    sample = next(x for x in scvi['ipynb_paths'] if x['path'].endswith('api_overview.ipynb'))
    raw = api(f"repos/{scvi['repository']}/contents/{sample['path']}?ref={scvi['revision']}")
    content = base64.b64decode(raw['content'])
    notebook = json.loads(content)
    assert notebook['nbformat'] == 4 and any(c['cell_type'] == 'code' for c in notebook['cells'])
    summary = {'mapped_sources': len(rows), 'mapped_none_detected': sum(r['status'] == 'none_detected' for r in rows), 'mapped_unknown': sum(r['status'] == 'unknown' for r in rows), 'with_submodules': sum(bool(r.get('submodules')) for r in rows), 'negative_with_submodules': sum(r['status'] == 'none_detected' and bool(r.get('submodules')) for r in rows), 'positive_with_submodules': sum(r['status'] == 'present' and bool(r.get('submodules')) for r in rows)}
    evidence = {'observed_at': now(), 'scope': 'Four purposively selected pinned submodule probes; file discovery only, one notebook parsed, no execution or suitability review.', 'baseline_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(), 'summary': summary, 'findings': findings, 'parsed_notebook': {'repository': scvi['repository'], 'revision': scvi['revision'], 'path': sample['path'], 'sha256': hashlib.sha256(content).hexdigest(), 'cells': len(notebook['cells']), 'code_cells': sum(c['cell_type'] == 'code' for c in notebook['cells'])}, 'requests': requests}
    (ROOT/'evidence.json').write_text(json.dumps(evidence, indent=2) + '\n')
    print(json.dumps(summary), flush=True)
    return {'start': started, 'end': now(), 'exit_status': 0, 'estimate_mib': 100, 'initial_resources': initial, 'final_resources': guard(), 'peak_self_rss_kib': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss, 'peak_child_rss_kib': resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss}


if __name__ == '__main__':
    run = main()
    (ROOT/'run.json').write_text(json.dumps(run, indent=2) + '\n')
    print(json.dumps(run))
