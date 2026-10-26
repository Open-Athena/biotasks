"""Publish only the reviewed, fully cleaned bounded-run metric checkpoint."""
from pathlib import Path
import json
from biotasks.validation import preservation

root = Path(__file__).resolve().parent
metadata = {
    'scope': 'Own numeric/provenance checkpoint at the original CPU guard, including offline argv-size diagnosis. No raw tasks, source/test patches, traces or biological data.',
    'public_eligibility': 'Reviewed own metrics, enums, static explanations and hashes only; no credentials, environments or third-party raw text.',
    'source_revision': 'e96fefd9',
    'visibility': 'public',
    'retention': 'Retain while issue33/67 conclusions depend on this original bounded-run checkpoint.',
}
directory = root/'summary-archive-003'
directory.mkdir(exist_ok=True)
preservation.prepare(directory, {'bounded-reassessment-summary.json':root/'bounded-reassessment-summary-001.json'}, metadata)
with preservation.transfer_limits(directory):
    preservation.publish(directory, {'kind':'hf-public','bucket':'open-athena/biotasks','prefix':'research/67-broader-pr-yield'}, {'eligible':True,'review':metadata['public_eligibility']})
receipt = json.loads((directory/'publication.json').read_text())
assert receipt['anonymous_download_verified']
print(json.dumps({'prefix':receipt['prefix'],'anonymous_readback_verified':True,'objects':len(receipt['objects'])}))
