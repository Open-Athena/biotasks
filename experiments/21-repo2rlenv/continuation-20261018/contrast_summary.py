"""Emit bounded native contrast/cleanup metadata without exporting worker secrets."""
import hashlib
import json
import tarfile
from pathlib import Path


def summarize(source, output):
    source, output = Path(source), Path(output)
    record = {'stage': 'native_mutation_contrast_summary', 'model_calls': 0, 'generation_available': False}
    result = source / 'result.json'
    if result.is_file():
        data = json.loads(result.read_text())
        record['controller'] = {k: data[k] for k in ('status', 'stage', 'worker_returncode', 'cleanup', 'execution_timeout_sec') if k in data}
    workers = []
    for path in sorted((source / 'workers').glob('*.json')):
        data = json.loads(path.read_text())
        workers.append({k: data[k] for k in ('worker_id', 'state', 'started_at', 'ready_at', 'stopped_at') if k in data})
    record['workers'] = workers
    archive = source / 'native-evidence.tar.gz'
    if archive.is_file():
        record['native_archive_bytes'] = archive.stat().st_size
        with archive.open('rb') as stream:
            record['native_archive_sha256'] = hashlib.file_digest(stream, 'sha256').hexdigest()
        with tarfile.open(archive, 'r|gz') as handle:
            for member in handle:
                if member.name == 'native/generation/generation.json':
                    if not member.isfile() or member.size > 1024**2:
                        raise ValueError('Unexpected generation summary member')
                    raw = handle.extractfile(member).read()
                    data = json.loads(raw)
                    if not 0 <= data['attempted'] <= 10 or len(data['candidates']) + len(data['rejected']) != data['attempted']:
                        raise ValueError('Incomplete or inconsistent candidate counters')
                    record.update(generation_available=True, generation_json_sha256=hashlib.sha256(raw).hexdigest(), attempted=data['attempted'], execution_passed=len(data['candidates']), rejected=len(data['rejected']), candidates=[{k: item[k] for k in ('id', 'entity', 'source_file') if k in item} for item in data['candidates']])
                    break
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(record, indent=2) + '\n')
    return record
