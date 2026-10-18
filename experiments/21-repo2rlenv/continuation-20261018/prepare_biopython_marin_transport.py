"""Explicit Marin collection profile for Biopython's known LICENSE link.

The license text, target file, task environment, instruction, oracle and tests
stay unchanged. This materializes one verified in-repository license link as an
ordinary file before Marin's supported workspace transfer. Other link checks in
Marin remain unchanged. Original failed mappings are retained separately.
"""
import hashlib
import json
import shutil
from pathlib import Path


def normalization_program(root, expected_sha256):
    return f'''import hashlib,json,os
from pathlib import Path
root=Path({str(root)!r})
path=root/'LICENSE'
target=root/'LICENSE.rst'
assert target.is_file() and not target.is_symlink()
data=target.read_bytes()
assert hashlib.sha256(data).hexdigest()=={expected_sha256!r}
mode=target.stat().st_mode & 0o777
if path.is_symlink():
    assert os.readlink(path)=='LICENSE.rst'
    before='symlink:LICENSE.rst'
    path.unlink()
    path.write_bytes(data)
    path.chmod(mode)
else:
    assert path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest()=={expected_sha256!r}
    before='ordinary_file'
assert not path.is_symlink() and hashlib.sha256(path.read_bytes()).hexdigest()=={expected_sha256!r}
print(json.dumps({{'before':before,'after':'ordinary_file','sha256':{expected_sha256!r},'bytes':len(data),'mode':oct(path.stat().st_mode & 0o777)}}))
'''


def materialized_probe(root, expected_sha256):
    return f'''import hashlib,json
from pathlib import Path
path=Path({str(root)!r})/'LICENSE'
assert path.is_file() and not path.is_symlink()
data=path.read_bytes()
assert hashlib.sha256(data).hexdigest()=={expected_sha256!r}
print(json.dumps({{'kind':'ordinary_file','sha256':{expected_sha256!r},'bytes':len(data),'mode':oct(path.stat().st_mode & 0o777)}}))
'''


def prepare(original_roots, license_files, destination):
    destination.mkdir(exist_ok=False)
    records = []
    for pr, original in original_roots.items():
        source_spec = original / 'task.json'
        old = json.loads(source_spec.read_text())
        assert old['source']['row'].startswith('biopython/biopython#') and old['id'].startswith('repo2rlenv-pr-runtime/')
        assert not old['grader'].get('collect')
        license_bytes = license_files[pr].read_bytes()
        sha = hashlib.sha256(license_bytes).hexdigest()
        program = normalization_program('/workspace', sha)
        probe = materialized_probe('/workspace', sha)
        spec = json.loads(source_spec.read_text())
        spec['grader']['collect'] = [{'argv': ['python', '-c', program], 'cwd': '/workspace'}]
        identity = hashlib.sha256(json.dumps({'native_id': old['id'], 'collect': spec['grader']['collect']}, sort_keys=True).encode()).hexdigest()
        spec['id'] = 'repo2rlenv-pr-runtime-license-file/' + identity
        spec['source']['importer_revision'] = 'sha256:' + hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
        spec['tags'] = [tag for tag in spec['tags'] if tag != 'conversion-unvalidated'] + ['license-file-transport-unvalidated']
        assert spec['context'] == old['context'] and spec['resources'] == old['resources']
        assert spec['environment_requirements'] == old['environment_requirements']
        assert {k: v for k, v in spec['grader'].items() if k != 'collect'} == old['grader']
        controls = json.loads((original / 'controls.json').read_text())
        controls['license_transport'] = {'normalization_program': program, 'materialized_probe': probe, 'target_sha256': sha, 'source_link': 'LICENSE -> LICENSE.rst', 'scope': 'This known license link only; other Marin link rejection unchanged.'}
        out = destination / f'pr{pr}'
        out.mkdir()
        (out / 'task.json').write_text(json.dumps(spec, indent=2) + '\n')
        (out / 'controls.json').write_text(json.dumps(controls, indent=2) + '\n')
        shutil.copyfile(license_files[pr], out / 'source-LICENSE.rst')
        records.append({'pr': pr, 'repository': 'biopython/biopython', 'task_spec': f'pr{pr}/task.json', 'control_inputs': f'pr{pr}/controls.json', 'original_task_spec_sha256': hashlib.sha256(source_spec.read_bytes()).hexdigest(), 'original_task_id': old['id'], 'transport_profile_task_id': spec['id'], 'license_sha256': sha, 'cases': len(controls['cases']), 'native_instruction_environment_oracle_verifier_preserved': True})
    manifest = {'stage': 'explicit_license_file_transport_profile_prepared_not_validated', 'marin_revision': '45a044387ccd95ab698b4a592056aadaff961540', 'records': records, 'expected_pairs': sum(r['cases'] for r in records), 'native_plus_Marin_executions': 2 * sum(r['cases'] for r in records), 'model_calls': 0, 'blind_attempts': 0, 'Atlas_admissions': 0, 'profile_intervention': 'Supported grader.collect materializes only verified LICENSE -> LICENSE.rst as an ordinary byte-identical file. Native control path applies the same transport-only normalization before grading.', 'limitations': ['Original failed mappings remain preserved.', 'All runtime and reward parity claims require fresh remote execution.', 'Do not infer generic link support or weaken Marin archive checks.', 'No biology source, test, oracle, reward or instruction change.']}
    manifest['files'] = {file.relative_to(destination).as_posix(): {'bytes': file.stat().st_size, 'sha256': hashlib.sha256(file.read_bytes()).hexdigest()} for file in sorted(destination.rglob('*')) if file.is_file()}
    (destination / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    return manifest
