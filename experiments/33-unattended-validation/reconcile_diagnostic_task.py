"""Keep the MACS diagnostic outside the frozen 83-export cohort denominator."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TREE = ROOT.parents[2]
OLD = TREE/'31/experiments/31-historical-builds'
NEW = TREE/'34/experiments/34-offline-rebuild'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def normalized(files):
    return {row['path'].split('macs3-project__MACS-742/', 1)[1]:
        {key:row[key] for key in ('sha256', 'bytes', 'mode')} for row in files}


def content_id(files):
    return hashlib.sha256(json.dumps(files, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def main():
    cohort = json.loads((ROOT/'task-execution-ledger.json').read_text())
    assert 'macs3-project__MACS-742' not in {task['task'] for task in cohort['tasks']}
    inputs = [ROOT/'task-execution-ledger.json', OLD/'macs-742-export-manifest.json',
        OLD/'macs-native-742-manifest.json', OLD/'macs-742-control-results.json',
        NEW/'offline-export-manifest.json', NEW/'macs-742-control-results.json']
    original = json.loads(inputs[1].read_text())
    refs = json.loads(inputs[2].read_text())
    first = normalized(original['files'])
    offline = normalized(json.loads(inputs[4].read_text())['task_files'])
    assert len(first) == 10 and len(offline) == 12
    assert sum(first[name] == offline.get(name) for name in first) == 9
    attempts = []
    for issue, path, inventory in [(31, inputs[3], first), (34, inputs[5], offline)]:
        value = json.loads(path.read_text())
        attempts.append(dict(issue=issue, source=path.name, archive_sha256=value['archive_sha256'],
            task_content_id=content_id(inventory), positive_control_pair=value['pairs'][0]['positive_control_pair'],
            clean_oracle_command=value['pairs'][0]['clean_oracle_command']))
    confirmation = NEW/'confirmation-readback.json'
    if confirmation.exists():
        inputs.append(confirmation)
        value = json.loads(confirmation.read_text())
        manifest = NEW/'inputs-private/confirmation-output/candidate-manifest.json'
        if manifest.exists():
            inventory = normalized(json.loads(manifest.read_text())['task_files'])
            assert sum(first[name] == inventory.get(name) for name in first) == 9
            inputs.append(manifest)
        else:
            inventory = {}
        attempts.append(dict(issue=34, source=confirmation.name, archive_sha256=value['archive_sha256'],
            task_content_id=content_id(inventory) if inventory else None,
            positive_control_pair=value['pair']['positive_control_pair'],
            clean_oracle_command=value['pair']['clean_oracle_command'],
            dependency_preparation_verified=value['dependency_preparation_verified']))
    result = dict(task='macs3-project__MACS-742', base_commit=refs['base_sha'], head_commit=refs['head_sha'],
        cohort='Separate #31/#34 diagnostic task; excluded from the frozen #28 cohort denominator',
        original_cohort_counts=cohort['counts'], original_task_content_id=content_id(first),
        original_files=first, offline_candidate_content_id=content_id(offline),
        original_non_dockerfile_assets_unchanged=9, control_attempts=attempts,
        sources_sha256={str(p):digest(p) for p in inputs},
        limits=['Repeated MACS controls are attempts for one diagnostic task',
            'Export uses the pinned upstream writer on reconstructed evidence, not a fresh generate CLI run',
            'Image identity and dependency provenance are attempt-specific'])
    (ROOT/'diagnostic-task-ledger.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(dict(diagnostic_tasks=1, recorded_control_attempts=len(attempts), frozen_cohort_unchanged=True)))


if __name__ == '__main__':
    main()
