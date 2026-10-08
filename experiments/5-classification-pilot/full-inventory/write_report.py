"""Render the final evidence report from checked inventory outputs."""
import json
from collections import Counter
from pathlib import Path
ROOT=Path(__file__).resolve().parent
s=json.loads((ROOT/'summary.json').read_text());c=json.loads((ROOT/'classification-summary.json').read_text());v=json.loads((ROOT/'vocabulary.json').read_text())
lines=['# Full-inventory reassessment and classification','',
'The source inspection and inventory-wide classification pass is complete. Every recorded location has an outcome; labels distinguish individual source review from provisional rule assignments. This is not a fully adjudicated biological classification or a notebook-execution study. The original discovery registry remains unchanged as the historical baseline.','',
'## Inventory result','',
'| Measure | Result |','| --- | ---: |',
f"| Distinct notebook/literate authoring locators | **{s['authoring_locators']:,}** |",
f"| Content-confirmed authoring documents | {s['content_confirmed_documents']:,} |",
f"| Historical authoring locators still unresolved | {s['authoring_locators']-s['content_confirmed_documents']} |",
f"| Distinct documents with a repository location | {s['across_repositories']:,} |",
f"| Other package/archive/documentation locations | {s['outside_repositories']:,} |",
f"| Repositories with retained documents | {s['repositories_with_documents']} |",
f"| Repository rows, including zero counts | {s['repositories']} |",
f"| Rendered-only fallbacks, separate | {s['rendered_fallbacks']} |",'',
'Count reconciliation: **4,277 baseline + 15 inspected additions − 28 non-authoring references/format collisions − 19 additional exact-byte duplicate locations = 4,245 distinct authoring locators**. The 28 exclusions comprise 25 Git symlink references, one bitmap `.dib`, one LAMMPS `.Nb` input and one ordinary Python script named `.ipynb`. Symlinks retain pinned tree-mode and target evidence. Valid empty/test notebooks remain in the all-format inventory. No exclusion is based merely on Jupyter versus another format.','',
f"Per-repository counts sum to {s['repository_attributions']:,}; a shared document may belong to several repositories. The global total deduplicates exact original bytes and preserves aliases. [Repository counts](repository-counts.csv), [source-project counts](source-counts.csv), [summary](summary.json), [format corrections](format-corrections.jsonl) and [complete source outcomes](acquisition.jsonl) preserve the accounting.",'',
'## Classification and vocabulary','',
f"The working vocabulary now has **{len(v['scientific_field'])} scientific fields, {len(v['modality'])} modalities and {len(v['operation'])} operations**. [Vocabulary](vocabulary.md) and [machine-readable definitions](vocabulary.json) retain the separate facets and overlapping labels. [Open the offline explorer](inventory.html) to inspect notebooks, independent repository scope, evidence, review states and filtered CSV exports. The Distributions tab shows document categories across all three axes, reviewed versus provisional labels, facet coverage, independent repository scope, repository size bins, the 20 largest collections and authoring formats. Category bars drill through to source records; percentages and denominators are explicit, and overlapping categories are not summed.",'',
'- Broader sources added biomedical informatics and synthetic biology/biomolecular engineering. Clinical records and biomedical question answering fit the former; protein design required the latter. Generic language modeling, chemical structures and protein embeddings do not automatically establish a biological field.',
'- Added medical images, clinical records, chemical structures without assays, biomedical text and structured biological relationships as modalities. Input origin and assay details remain separate metadata.',
'- Added feature/representation extraction, sequence/probe design and sequence database search. Constructing a model, simulating it, fitting an inverse problem, and consuming its outputs remain distinct.',
'- Final contrasting reviews checked structure ranking versus sequence design, simulated neurons versus recorded electrophysiology, generic information extraction versus biomedical questions, and model-design preparation versus fitted inference. These two last batches required no further terms. They are purposive same-assistant checks, not an independent holdout or proof of permanent saturation.','',
f"Individual review covers **57 source versions/documents**: the earlier 35 plus 22 new reviews. Exact-byte transfer is explicitly recorded where applicable. The remaining assignments are **provisional source-pattern classifications**, not silently promoted to reviewed scientific judgments. [Reviewed expansion](reviewed-annotations.jsonl), [all annotations](annotations.jsonl) and [auditable rules](rules.py) are available separately.",'',
'| Scientific-field state, distinct counted documents | Count |','| --- | ---: |']
for state,count in c['facet_coverage']['scientific_field'].items():lines.append(f'| {state} | {count:,} |')
lines+=['',
'Unassigned fields are not automatically generic infrastructure: they remain insufficient evidence unless an individual review explicitly records “not applicable.” Provisional operation signatures likewise retain unadjudicated roles/targets. This disclosure is part of the result; the pass does not claim full manual classification or benchmark ground truth. Repository labels come from separate root README inspection, never from sampled notebooks. The explorer defaults to distinct counted documents and can expose duplicate/excluded records for audit.','',
'## Acquisition, checks and limits','',
'All 4,301 locations (the 4,286-record baseline including nine rendered fallbacks, plus 15 additions) received an outcome. Oversized notebooks were recovered with a streaming JSON parser that discards outputs. One known 72,238,389-byte file used a targeted 96 MiB transfer cap and verified Git blob identity. Eleven recovered `www.github.com` links were pinned and verified byte-for-byte. The remaining six unresolved locators are five dead external links and one malformed notebook. They remain distinguishable from confirmed content.','',
'All 952 repository rows received a separate bounded root-README check; unavailable descriptions remain explicit. Static acquisition and processing used one worker, shared resource locking and bounded memory. Raw upstream text stays in ignored local caches; versioned manifests, hashes, evidence locators and executable research inputs support reacquisition. No biological analyses, solver/model calls, paid compute or notebook environments were executed.','',
'[Validation](validation.json) checks source identity, evidence locators, vocabulary membership, exact-byte duplicate groups, per-repository/global arithmetic, unchanged baseline hash and format regressions. [Browser validation](browser-validation.json) checks search, filters, evidence expansion, CSV export and mobile/desktop rendering. These checks do not independently validate biological judgments.','',
'## Reproduction','',
'Under the AGENTS.md resource guard and shared lock, run acquire.py, acquire_repositories.py, recover.py (ijson 3.5.1), recover_final_source.py and resolve_external_github.py as needed. Preserve original attempts and later recovery records. Run correct_formats.py **before** recover_final_source.py so the latter appends the full plain-script verification. Then run review_expansion.py, classify.py, build_explorer.py, validate.py and check_browser.py. The last browser check uses the installed Chromium and the retained Playwright environment. Shared resource limits apply to each acquisition/build/check. Source caches are ignored; no inspected notebook code is executed.','',
'Acquisition, recovery and stage-run ledgers record timings, exit states and memory. [Execution correction](execution-corrections.json) identifies the one earlier run whose original script fingerprint was computed after a queued edit; subsequent runs capture launch fingerprints. The source registry and prior published findings are preserved rather than overwritten.','']
(ROOT/'README.md').write_text('\n'.join(lines))
lines=['# Working classification vocabulary '+v['version'],'','Source-evidenced navigation categories, not an adopted ontology. Categories overlap. Rule assignments remain provisional. Repository and document subjects are distinct.','']
for facet,title in [('scientific_field','Scientific field'),('modality','Data modality'),('operation','Analytical operation')]:
 lines += ['## '+title,'','| ID | Label | Definition |','| --- | --- | --- |']
 for term,t in v[facet].items():lines.append(f"| `{term}` | {t['label']} | {t['definition']} |")
 lines.append('')
(ROOT/'vocabulary.md').write_text('\n'.join(lines))
print('Rendered final report and vocabulary.')
