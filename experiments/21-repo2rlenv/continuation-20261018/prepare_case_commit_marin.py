"""Prepare the admitted ASCII-case commit TaskSpec with its native identity.

The PR-shaped directory is only a retained control-storage convention. It must
not turn the commit source into a PR task or create a new scientific competency.
"""

import hashlib
import json
import tomllib
from pathlib import Path

from prepare_pr_marin_parity import prepare as prepare_controls


def prepare(evidence, destination):
    manifest = prepare_controls(evidence, destination, selected_prs={2630})
    assert len(manifest['records']) == 1
    original = tomllib.loads((evidence / 'pr2630/portable/task/task.toml').read_text())
    metadata = original['metadata']['repo2env']
    assert metadata['pipeline'] == 'commit_runtime' and metadata['repo'] == 'scikit-bio/scikit-bio'
    commit = metadata['commit_runtime']
    assert commit['commit_sha'] == 'd25f305cea3a6cc200b0fe10806151132b395bcf'
    spec_file = destination / 'pr2630/task.json'
    spec = json.loads(spec_file.read_text())
    preserved = {key: spec[key] for key in ('context', 'environment_requirements', 'resources', 'grader', 'output_paths')}
    row = manifest['records'][0]
    identity = row['portable_asset_sha256']
    spec['id'] = 'repo2rlenv-commit-runtime/' + identity
    spec['source']['row'] = metadata['repo'] + '@' + commit['commit_sha']
    spec['source']['importer_revision'] = 'sha256:' + hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    spec['tags'] = ['commit_runtime' if tag == 'pr_runtime' else tag for tag in spec['tags']]
    assert {key: spec[key] for key in preserved} == preserved
    spec_file.write_text(json.dumps(spec, indent=2) + '\n')
    row.update(route='commit_runtime/native', native_task_id=original['task']['name'],
               commit=commit['commit_sha'], parent=commit['parent_sha'],
               control_storage_alias='pr2630', stable_task_id=spec['id'])
    manifest.update(stage='commit_identity_mapping_prepared_not_schema_or_runtime_validated',
                    native_instruction_environment_oracle_grader_bytes_preserved=True,
                    source_fix_family_shared_with_PR2630=True)
    manifest['files'] = {
        file.relative_to(destination).as_posix(): {
            'bytes': file.stat().st_size, 'sha256': hashlib.sha256(file.read_bytes()).hexdigest()}
        for file in sorted(destination.rglob('*')) if file.is_file() and file.name != 'manifest.json'}
    (destination / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    return manifest
