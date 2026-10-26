"""Publish reviewed aggregate counts; keep original raw historical evidence private."""
from pathlib import Path
import json
from biotasks.validation import preservation

root = Path(__file__).resolve().parent
sources = {'generation-summary.json': root/'generation-summary-002.json', 'cleanup-recovery-summary.json': root/'cleanup-recovery-summary-001.json'}
metadata = {
    'scope': 'Own aggregate generation results, original-control cleanup recovery and reporting reconciliation. No task bundles, raw logs, code patches or biological data.',
    'public_eligibility': 'Reviewed numeric, enum, static explanatory and provenance allowlist. No third-party raw text, credentials or environments.',
    'source_revision': '267da67f',
    'visibility': 'public',
    'retention': 'Retain while issue33/67 research conclusions depend on this snapshot.',
}
directory = root/'summary-archive-002'
directory.mkdir(exist_ok=True)
preservation.prepare(directory, sources, metadata)
with preservation.transfer_limits(directory):
    preservation.publish(directory, {'kind':'hf-public', 'bucket':'open-athena/biotasks', 'prefix':'research/67-broader-pr-yield'}, {'eligible':True, 'review':metadata['public_eligibility']})
receipt = json.loads((directory/'publication.json').read_text())
assert receipt['anonymous_download_verified']
print(json.dumps({'prefix':receipt['prefix'], 'anonymous_readback_verified':True, 'objects':len(receipt['objects'])}))
