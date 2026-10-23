"""Bind verified PR742 validation inputs to the retained replay image."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def main():
    manifest_path = ROOT / 'macs-native-742-manifest.json'
    manifest = json.loads(manifest_path.read_text())
    result = json.loads((ROOT / 'macs-742-image-result-001.json').read_text())
    readback = json.loads((ROOT / 'macs-742-image-readback-001.json').read_text())
    account = json.loads((ROOT / 'macs-742-image-accounting.json').read_text())
    submission = json.loads((ROOT / 'run-private/biotasks31-macs-742-image-001/submission.json').read_text())
    assert account['state'] == 'succeeded' and account['attempts'] == 1 and account['exit_code'] == 0
    assert readback['archive_sha256'] == account['output_archive']['sha256']
    assert readback['result_record_verified'] and readback['cleanup_verified']
    assert readback['owned_containers_absent'] and readback['context_tools_removed']
    assert result['run_id'] == 'biotasks31-macs-742-image-001' and result['model_calls'] == 0
    assert result['replay']['status'] == 'matched_recorded_exits' and len(result['replay']['steps']) == 16
    assert result['smoke_passed'] and result['verify_passed']
    assert result['retained_image_id'] == readback['retained_image_id']
    assert result['retained_image_tag'] == 'biotasks31-macs-742-image-001:recorded-actions'
    assert result['cleanup_verified'] and not result.get('error')
    assert submission['worker_id'] and submission['state'] == 'submitted'
    fields = {
        'image_id': result['retained_image_id'],
        'image_tag': result['retained_image_tag'],
        'image_owner': result['run_id'],
        'image_worker_id': submission['worker_id'],
        'image_archive_sha256': readback['archive_sha256'],
        'image_reconstruction_allocated_cpu_hours': account['allocated_cpu_hours'],
        'live_execution': False,
    }
    for key, value in fields.items():
        if key in manifest and key != 'live_execution':
            assert manifest[key] == value
    manifest.update(fields)
    manifest_path.write_text(json.dumps(manifest, indent=2) + '\n')
    print(json.dumps(fields))


if __name__ == '__main__':
    main()
