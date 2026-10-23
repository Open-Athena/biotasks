"""Bind a read-only assessment of native image distribution to pinned sources."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TREE = ROOT.parents[2]
PRIOR = TREE/'31/experiments/31-historical-builds'
PACKAGE = PRIOR/'inputs-private/upstream-package'
REVISION = '27d04ee8203cd5b2f20c3997d13836e5f5b64238'


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    acquisition = json.loads((PRIOR/'package-acquisition.json').read_text())
    assert acquisition['revision'] == REVISION
    by_path = {row['path']:row for row in acquisition['files']}
    references = {
        'src/repo2rlenv/cli.py': [[1140, 1182], [1242, 1242]],
        'src/repo2rlenv/spec/input.py': [[267, 277]],
        'src/repo2rlenv/bootstrap/runner.py': [[300, 316], [693, 715]],
        'src/repo2rlenv/bootstrap/docker.py': [[237, 253], [328, 356]],
        'src/repo2rlenv/pipelines/pr_runtime.py': [[362, 374], [1114, 1125]],
        'src/repo2rlenv/emitter/harbor.py': [[99, 119]],
        'src/repo2rlenv/registry/integration.py': [[408, 437], [549, 632]],
        'src/repo2rlenv/hub.py': [[398, 455]],
    }
    sources = []
    for path, ranges in references.items():
        data = (PACKAGE/path).read_bytes()
        expected = by_path[path]
        assert len(data) == expected['bytes'] and hashlib.sha256(data).hexdigest() == expected['sha256']
        assert hashlib.sha1(f'blob {len(data)}\0'.encode()+data).hexdigest() == expected['git_blob']
        sources.append(dict(path=path, sha256=expected['sha256'], git_blob=expected['git_blob'],
            relevant_lines=ranges, url=f'https://github.com/huggingface/Repo2RLEnv/blob/{REVISION}/{path}'))
    baseline = TREE/'34/experiments/34-offline-rebuild'
    manifest = json.loads((baseline/'offline-export-manifest.json').read_text())
    cleanup = json.loads((baseline/'macs-742-image-cleanup-readback-001.json').read_text())
    assert cleanup['result']['verified_empty'] and cleanup['result']['remaining_images'] == []
    result = dict(main_revision='2a1950d239f1ada467c35393991dac87debe35f7', upstream_revision=REVISION,
        assessed_utc=datetime.now(timezone.utc).isoformat(), source_files=sources,
        acquisition_manifest_sha256=sha(PRIOR/'package-acquisition.json'),
        baseline=dict(task='macs3-project__MACS-742', local_image_id=manifest['image_id'],
            image_removed=True, manifest_sha256=sha(baseline/'offline-export-manifest.json'),
            cleanup_readback_sha256=sha(baseline/'macs-742-image-cleanup-readback-001.json')),
        findings=[
            'Native bootstrap image_registry setting supports pushing and resolving a registry-qualified digest.',
            'Native pr_runtime selects registry digest for pushed bootstrap images and local tag otherwise.',
            'Native push-time prepare_dataset_for_push handles registry distribution and explicit inline recipes without uploading to HF itself.',
            'Native push_to_hub creates a dataset repository and invokes preparation before upload; it is not a read-only inspection entrypoint.',
            'Inline mode requires an existing cached bootstrap Dockerfile and rewrites task Dockerfile plus reproducibility metadata.',
            'A push-success path can retain a local image ID if RepoDigests resolution returns none; fresh-worker validation must require a pullable reference.',
        ],
        recommendation='Assess the existing native registry or explicit inline path before adding image-distribution infrastructure.',
        unverified=['Approved registry destination and write authorization', 'Image size and redistribution inventory',
            'Recipe-cache compatibility of the diagnostic bundle', 'Fresh-worker pull/build and nop/oracle controls',
            'Availability and exact identity of dependencies during future reconstruction'],
        stage='Source assessment only', source_package_executed=False, model_calls=0,
        remote_jobs=0, uploads=0, new_budget=False)
    (ROOT/'source-assessment.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(dict(upstream_revision=REVISION, source_files_verified=len(sources), source_package_executed=False, remote_jobs=0)))


if __name__ == '__main__':
    main()
