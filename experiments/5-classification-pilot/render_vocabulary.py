"""Render the editable vocabulary companion from the versioned term definitions."""
import json
from pathlib import Path
root = Path(__file__).resolve().parent
v = json.loads((root/'vocabulary.json').read_text())
lines = ['# Draft classification vocabulary '+v['version'], '',
'This is a working navigation vocabulary, not an adopted ontology. Terms overlap. Exercised means at least one pilot assignment, not independent validation. See [working rules](decisions.md) for field/setting boundaries and operation roles.', '',
'Use scientific field for browsing, data modality for observations/inputs, and operation for analytical work. Keep file format, input origin, assay subtype, design and biological setting separate. An assignment needs subject/revision, evidence, rationale and review status. Operation assignments also need a role and target. No automatic repository-to-notebook inheritance.', '',
'Review states for a facet are unreviewed, content-supported, insufficient evidence, not applicable or disputed. Label-level states can be suggested, content-supported, needs-review or rejected. Do not force a biological field onto a generic utility. None of these states claims executable validation.', '']
for facet,title in [('scientific_field','Scientific field'),('modality','Data modality'),('operation','Analytical operation')]:
 lines += ['## '+title,'','| ID | Label | Definition | Pilot |','| --- | --- | --- | --- |']
 for key,t in v[facet].items():
  lines.append(f"| `{key}` | {t['label']} | {t['definition']} | {'Exercised' if t['pilot_status']=='exercised_in_sample' else 'Untested proposal'} |")
 lines.append('')
(root/'vocabulary.md').write_text('\n'.join(lines))
