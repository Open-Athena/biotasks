"""Archive only reviewed aggregate results; raw historical evidence stays private."""
from pathlib import Path
import json
from biotasks.validation import preservation

root=Path(__file__).resolve().parent
sources={'summary.json':root/'generation-summary-001.json'}
metadata={'scope':'Own aggregate NiBabel generation results and connector recovery; not task bundles, logs, source patches or data.',
          'public_eligibility':'Reviewed explicit numeric/enum/provenance allowlist. No third-party raw text, credentials, environments or biological data.',
          'source_revision':'9e8e8408','visibility':'public','retention':'Retain while the issue33/67 research conclusions depend on this snapshot.'}
directory=root/'summary-archive-001'
directory.mkdir(exist_ok=True)
preservation.prepare(directory,sources,metadata)
with preservation.transfer_limits(directory):
    preservation.publish(directory,{'kind':'hf-public','bucket':'open-athena/biotasks','prefix':'research/67-broader-pr-yield'}, {'eligible':True,'review':metadata['public_eligibility']})
receipt=json.loads((directory/'publication.json').read_text());assert receipt['anonymous_download_verified']
print(json.dumps({'prefix':receipt['prefix'],'anonymous_readback_verified':True,'objects':len(receipt['objects'])}))
