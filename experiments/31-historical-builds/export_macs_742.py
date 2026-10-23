"""Emit one PR742 candidate through pinned Repo2RLEnv's task writer.

This reuses archived PR/bootstrap inputs and the verified native outcome. It
does not invoke discovery, bootstrap, generation, a model, Docker or Harbor.
"""
import gzip
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import tempfile
import tomllib

ROOT = Path(__file__).resolve().parent
PRIVATE = ROOT / 'inputs-private/macs-742-export'


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def original_records():
    archive = ROOT / 'inputs-private/original-phase.tar.gz'
    with tarfile.open(archive) as tar:
        base = 'bootstrap/macs3-project__MACS/88c82d62d239__74ba7084/bootstrap.json'
        boot = json.load(tar.extractfile(base))
        discovery = json.loads(gzip.decompress(tar.extractfile('native-observations/batch-0003/discovery-pr-742.json.gz').read()))
    return boot, discovery


def main():
    manifest = json.loads((ROOT / 'macs-native-742-manifest.json').read_text())
    diagnosis = json.loads((ROOT / 'macs-742-native-diagnosis.json').read_text())
    assert diagnosis['native_f2p_pair_reported'] and diagnosis['exported_task'] is False
    assert diagnosis['archive_sha256'] == json.loads((ROOT / 'macs-742-native-accounting.json').read_text())['output_archive']['sha256']
    outcome = json.loads((ROOT / 'inputs-private/macs-742-native-001/rebuild/outcome.json').read_text())
    assert outcome['status'] == 'verified' and len(outcome['fail_to_pass']) == 1 and len(outcome['pass_to_pass']) == 10
    source_patch = (ROOT / 'inputs-private/macs-native-742/source.patch').read_text()
    test_patch = (ROOT / 'inputs-private/macs-native-742/test.patch').read_text()
    assert hashlib.sha256(source_patch.encode()).hexdigest() == manifest['files']['source.patch']['sha256']
    assert hashlib.sha256(test_patch.encode()).hexdigest() == manifest['files']['test.patch']['sha256']
    snapshot = json.loads((PRIVATE / 'issue-741.json').read_text())
    assert snapshot['number'] == 741 and snapshot['html_url'] == 'https://github.com/macs3-project/MACS/issues/741'
    boot_row, discovery = original_records()
    assert boot_row['repo'] == manifest['repo'] and boot_row['ref'] == '88c82d62d239d47b9c8ce9e545eeaaa6b7f695de'
    assert boot_row['rebuild_cmds'] == manifest['rebuild_cmds']
    assert discovery['number'] == manifest['pr'] and discovery['headRefOid'] == manifest['head_sha']
    source = ROOT / 'inputs-private/upstream-package'
    acquired = json.loads((ROOT / 'package-acquisition.json').read_text())
    assert acquired['revision'] == '27d04ee8203cd5b2f20c3997d13836e5f5b64238'
    for row in acquired['files']:
        assert sha(source / row['path']) == row['sha256']
    task_root = PRIVATE / 'task'
    assert not task_root.exists(), 'Never overwrite a previous emitted candidate'
    with tempfile.TemporaryDirectory(prefix='biotasks31-export-') as td:
        checkout = Path(td) / 'package'
        shutil.copytree(source, checkout)
        subprocess.run(['git', 'apply', str(ROOT / 'historical-rebuild.patch')], cwd=checkout, check=True, capture_output=True, timeout=5)
        for rel in ('spec/options.py', 'pipelines/pr_runtime.py', 'pipelines/pr_runtime_validate.py', 'pipelines/runtime_rebuild.py'):
            assert (checkout / 'src/repo2rlenv' / rel).read_bytes() == (ROOT / 'candidate' / rel).read_bytes()
        sys.path[:0] = [str(checkout / 'src'), str(ROOT / 'inputs-private/check-deps')]
        from repo2rlenv.bootstrap.spec import BootstrapResult, LanguageHint
        from repo2rlenv.cli import _parse_pipeline_opts
        from repo2rlenv.config import load_generation_input
        from repo2rlenv.emitter.harbor import write_harbor_task
        from repo2rlenv.github import PullRequestSummary
        from repo2rlenv.pipelines import PIPELINES
        from repo2rlenv.spec.options import parse_options

        boot_row['image_digest'] = manifest['image_id']
        boot_row['image_tag'] = manifest['image_tag']
        boot_row['smoke_passed'] = True
        boot_row['verify_passed'] = True
        boot_row['transcript_path'] = None
        boot_row['language'] = LanguageHint(boot_row['language'])
        boot_row['extra'] = {**boot_row.get('extra', {}), 'reconstructed_from_recorded_actions': True}
        boot = BootstrapResult(**boot_row)
        pr = PullRequestSummary(
            number=discovery['number'], title=discovery['title'], body=discovery['body'],
            state='merged', merged_at=discovery['mergedAt'], base_ref=discovery['baseRefName'],
            base_sha=manifest['base_sha'], head_sha=discovery['headRefOid'], is_draft=discovery['isDraft'],
            url=discovery['url'], changed_files=[row['path'] for row in discovery['files']],
        )
        config = PRIVATE / 'generation-input.json'
        config_row = {'repo': {'url': manifest['repo'], 'access': 'public'},
                      'pipeline': {'name': 'pr_runtime', 'options': _parse_pipeline_opts(['replay_bootstrap_rebuild=true'])},
                      'output': {'destination': str(PRIVATE), 'org': 'open-athena', 'dataset_name': 'macs-pr742-candidate'}}
        if config.exists():
            assert json.loads(config.read_text()) == config_row
        else:
            config.write_text(json.dumps(config_row, indent=2) + '\n')
            config.chmod(0o600)
        spec = load_generation_input(config)
        options = parse_options(spec.pipeline.name, spec.pipeline.options, recipe=spec.pipeline.recipe)
        pipeline = PIPELINES[spec.pipeline.name](spec, options, boot)
        assert pipeline.rebuild_cmds == manifest['rebuild_cmds']
        class FrozenIssue:
            @staticmethod
            def fetch_issue(owner, name, number, token=None):
                assert (owner, name, number) == ('macs3-project', 'MACS', 741) and token is None
                return snapshot['title'], snapshot['body']
        pipeline._provider = FrozenIssue
        task = pipeline._build_task(pr, source_patch, test_patch,
                                    fail_to_pass=outcome['fail_to_pass'], pass_to_pass=outcome['pass_to_pass'],
                                    validation_status='verified')
        assert task.name == 'macs3-project__MACS-742'
        assert snapshot['title'] in task.instruction and '## Validation' not in task.instruction
        assert task.repo2env['pr_runtime']['rebuild_cmds'] == manifest['rebuild_cmds']
        assert task.repo2env['pr_runtime']['fail_to_pass'] == outcome['fail_to_pass']
        assert task.repo2env['pr_runtime']['pass_to_pass'] == outcome['pass_to_pass']
        assert task.environment_dockerfile.startswith('FROM ' + manifest['image_tag'] + '\n', len('# Auto-generated by Repo2RLEnv pr_runtime\n'))
        emitted = write_harbor_task(task, task_root)
        config_toml = tomllib.loads((emitted / 'task.toml').read_text())
        assert config_toml['metadata']['repo2env']['pr_runtime']['validation_status'] == 'verified'
        assert config_toml['verifier']['timeout_sec'] == 300
        assert (emitted / 'tests/test.sh').read_text() == task.test_script
        assert (emitted / 'tests/f2p.json').exists() and (emitted / 'tests/p2p.json').exists()
        files = [{'path': str(p.relative_to(PRIVATE)), 'bytes': p.stat().st_size, 'sha256': sha(p),
                  'mode': format(p.stat().st_mode & 0o777, '03o')}
                 for p in sorted(emitted.rglob('*')) if p.is_file()]
        receipt = {'repo': manifest['repo'], 'pr': 742, 'issue_snapshot_sha256': sha(PRIVATE / 'issue-741.json'),
                   'original_phase_sha256': manifest['original_archive_sha256'],
                   'native_archive_sha256': diagnosis['archive_sha256'], 'image_id': manifest['image_id'],
                   'image_tag': manifest['image_tag'], 'pinned_upstream_revision': acquired['revision'],
                   'candidate_patch_sha256': sha(ROOT / 'historical-rebuild.patch'),
                   'task_id': task.name, 'files': files, 'f2p_count': len(outcome['fail_to_pass']),
                   'p2p_count': len(outcome['pass_to_pass']), 'verifier_timeout_seconds': 300,
                   'model_calls': 0, 'harbor_control_run': False,
                   'limits': ['Candidate export from archived PR/bootstrap/native records, not a fresh official generate CLI run',
                              'Reconstructed image and frozen public issue snapshot replace deleted original image and live issue lookup',
                              'No independent Harbor nop/oracle control or task-quality claim yet']}
        (ROOT / 'macs-742-export-manifest.json').write_text(json.dumps(receipt, indent=2) + '\n')
        print(json.dumps({key: value for key, value in receipt.items() if key not in ('files', 'limits')}))


if __name__ == '__main__':
    main()
