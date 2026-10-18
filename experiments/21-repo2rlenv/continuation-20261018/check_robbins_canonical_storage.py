"""Exercise storage restoration using the pinned Repo2RLEnv task exporter.

Run in the pinned generator environment. This creates only tiny generic files;
it does not build Docker images, execute target libraries or call a model.
"""
import json
import shutil
import tempfile
from pathlib import Path

from pack_robbins_evidence import canonicalize, inventory, restore
from repo2rlenv.emitter.bundle import TaskBundle, TaskFile, write_bundle


def check():
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        bundle = TaskBundle(
            name='generic-storage-example', org='open-athena',
            instruction='Generic storage fixture only.',
            files={
                'environment/Dockerfile': TaskFile.text('FROM scratch\n'),
                'environment/docker-compose.yaml': TaskFile.text('generic original compose\n'),
                'environment/source.py': TaskFile.text('value = 1\n'),
                'tests/test.sh': TaskFile.text('#!/bin/sh\nexit 0\n', executable=True),
                'tests/grade.py': TaskFile.text('generic unchanged grader\n'),
                'solution/solve.sh': TaskFile.text('#!/bin/sh\ntrue\n', executable=True),
            },
            metadata={'recipe': 'generic-storage-fixture', 'recipe_version': '1', 'reward_kinds': ['test_execution']},
        )
        parent = root / 'native-task'
        native = write_bundle(bundle, parent)
        assert native.parent == parent and native != parent
        original = inventory(native)
        profile = root / 'offline-task'
        shutil.copytree(native, profile)
        (profile / 'task.toml').write_text((profile / 'task.toml').read_text() + '\n# Generic runtime profile.\n')
        (profile / 'environment/docker-compose.yaml').unlink()
        cases, expected = [], {}
        for name, script in [('baseline', '#!/bin/sh\ntrue\n'), ('alternative', '#!/bin/sh\nprintf generic\n')]:
            destination = root / 'cases' / name
            shutil.copytree(profile, destination)
            (destination / 'solution/solve.sh').write_text(script)
            (destination / 'solution/solve.sh').chmod(0o755)
            cases.append({'case': name, 'bundle': str(destination)})
            expected[name] = inventory(destination)
        manifest = {
            'native_task_relative_path': native.relative_to(root).as_posix(),
            'native_assets': original, 'profile_assets': inventory(profile),
            'case_unchanged_assets': {k: v for k, v in inventory(profile).items() if k != 'solution/solve.sh'},
            'cases': cases,
        }
        (root / 'control-manifest.json').write_text(json.dumps(manifest))
        record = canonicalize(root)
        assert record['complete_native_task'] == native.relative_to(root).as_posix()
        assert not (root / 'cases').exists() and not profile.exists()
        assert inventory(native) == original
        for name in expected:
            restored = root / ('restored-' + name)
            restore(root, restored, name)
            assert inventory(restored) == expected[name]
        result = {
            'stage': 'pinned_native_exporter_storage_fixture_passed_no_target_execution',
            'actual_exporter_nested_task_path_exercised': True,
            'cases_reconstructed': len(expected), 'native_task_bytes_modes_preserved': True,
            'profile_metadata_delta_and_compose_deletion_preserved': True,
            'case_solution_bytes_modes_preserved': True,
            'redundant_copies_removed_only_after_reconstruction_verification': True,
            'model_calls': 0, 'native_control_results_claimed': False,
        }
        return result


if __name__ == '__main__':
    result = check()
    Path(__file__).with_name('robbins-canonical-storage-native-exporter-check.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))
