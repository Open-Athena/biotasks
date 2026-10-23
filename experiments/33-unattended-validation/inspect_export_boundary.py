"""Bind the PR742 network-guard finding and retained license notices to exact bytes."""
import argparse
import ast
import hashlib
import json
from pathlib import Path


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--baseline', type=Path, required=True)
    parser.add_argument('--followup', type=Path, required=True)
    args = parser.parse_args()
    baseline = args.baseline.resolve()
    followup = args.followup.resolve()
    package = json.loads((followup / 'package-acquisition.json').read_text())
    path = 'src/repo2rlenv/pipelines/_env_guard.py'
    guard = followup / 'inputs-private/upstream-package' / path
    recorded = next(row for row in package['files'] if row['path'] == path)
    assert sha(guard) == recorded['sha256']
    tree = ast.parse(guard.read_text())
    hosts = next(ast.literal_eval(node.value) for node in tree.body
                 if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name)
                 and node.target.id == 'FIX_SOURCE_HOSTS')
    export = json.loads((followup / 'macs-742-export-manifest.json').read_text())
    compose_path = 'task/macs3-project__MACS-742/environment/docker-compose.yaml'
    compose = followup / 'inputs-private/macs-742-export' / compose_path
    binding = next(row for row in export['files'] if row['path'] == compose_path)
    assert sha(compose) == binding['sha256']
    compose_text = compose.read_text()
    assert all('"' + host + ':0.0.0.0"' in compose_text for host in hosts)
    wrapper = followup / 'harbor_docker.py'
    wrapper_text = wrapper.read_text()
    assert 'extra_hosts' not in wrapper_text
    assert 'routed = args[:index] + ["-f", str(overlay)] + args[index:]' in wrapper_text
    manifest = json.loads((followup / 'macs-native-742-manifest.json').read_text())
    published = json.loads((baseline / 'history-wide/archives/macs3-project__MACS-manifest.json').read_text())
    published_files = {row['path']: row for row in published['files']}
    notices = []
    for ref in (manifest['base_sha'], manifest['head_sha']):
        rel = 'macs3-project__MACS/' + ref + '--LICENSE'
        notice = baseline / 'history-wide/source-notices' / rel
        key = 'source-notices/history/' + rel
        assert sha(notice) == published_files[key]['sha256']
        assert 'BSD 3-Clause License' in notice.read_text()
        notices.append({'ref': ref, 'notice_path': key, 'sha256': sha(notice), 'bytes': notice.stat().st_size,
                        'license': 'BSD-3-Clause', 'bound_to_prior_public_manifest': True})
    result = {
        'task': 'macs3-project__MACS-742', 'upstream_revision': package['revision'],
        'guard_source_sha256': sha(guard), 'task_compose_sha256': sha(compose),
        'resource_wrapper_sha256': sha(wrapper), 'task_blocks_hosts': list(hosts),
        'wrapper_preserves_task_compose_chain': True,
        'native_export_difference': 'Native validation has no generated task Compose overlay; exported Harbor task retains upstream PyPI/GitHub blackholes.',
        'finding': 'The added recorded rebuild needs a PyPI download inside a task that intentionally blackholes PyPI. This explains the refused dependency connection in both archived controls.',
        'evidence_limit': 'Source and frozen-config attribution plus existing execution logs; no new live DNS probe or successful offline rebuild is claimed.',
        'license_correction': 'GitHub null license metadata was not evidence that MACS had no usable source notice. Exact PR742 base/head BSD-3-Clause notices were already preserved in issue 28.',
        'notices': notices, 'model_calls': 0, 'remote_jobs': 0,
    }
    target = Path(__file__).resolve().parent / 'pr742-boundary-review.json'
    target.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
