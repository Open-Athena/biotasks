"""Source-only conversion check. Inputs are pinned by the development manifest."""
import hashlib
import json
from pathlib import Path
import sys

from biotasks.notebook_script import UnsupportedNotebook, export_python

manifest = json.loads(Path(sys.argv[1]).read_text())
output = Path(sys.argv[2])
output.mkdir(parents=True, exist_ok=False)
paths = [Path(value) for value in sys.argv[3:]]
if len(paths) != len(manifest['candidates']):
    raise SystemExit('Provide one original source per manifest candidate, in order')
results = []
for candidate, path in zip(manifest['candidates'], paths, strict=True):
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != candidate['source_sha256']:
        raise SystemExit('Source identity mismatch: ' + candidate['id'])
    if 'git_blob_sha1' in candidate:
        blob = b'blob ' + str(len(raw)).encode() + b'\0' + raw
        if hashlib.sha1(blob).hexdigest() != candidate['git_blob_sha1']:
            raise SystemExit('Git blob mismatch: ' + candidate['id'])
    result = {'id': candidate['id'], 'url': candidate['url'], 'source_sha256': candidate['source_sha256']}
    try:
        script, receipt = export_python(path)
    except UnsupportedNotebook as error:
        result.update(status='unsupported_conversion_profile', reason=str(error))
    else:
        # Verify deterministic repeat conversion; do not execute the source.
        assert export_python(path) == (script, receipt)
        receipt_path = output / (candidate['id'] + '.receipt.json')
        receipt_path.write_text(json.dumps(receipt, indent=2) + '\n')
        result.update(status='converted', receipt=receipt_path.name)
    results.append(result)
summary = {'scientific_execution': False, 'model_calls': 0, 'results': results}
(output / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
print(json.dumps({result['id']: result['status'] for result in results}, indent=2))
