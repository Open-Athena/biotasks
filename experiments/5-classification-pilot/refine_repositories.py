"""Materialize independent README judgments; never inherit document fields."""
import json
from pathlib import Path
root=Path(__file__).resolve().parent
rows=json.loads((root/'repository-annotations.json').read_text())[:8]
# fields, exact README anchor, rationale. Empty fields retain uncertainty.
specs=[
(['genomics-genetics'],'Genomics Data Analysis','Genomics tutorial and infrastructure collection.'),
(['immunology'],'single-cell immune receptor analysis','Immune repertoire scope; RNA assay alone does not establish expression-analysis scope.'),
([], 'developer version','Installation and status do not establish scientific scope.'),
(['bioimage-analysis'],'RGB image of a single plant','Plant image analysis is explicitly declared.'),
(['proteomics'],'processing mass spectrometry and proteomics data','Do not inherit metabolomics from the linked umbrella initiative.'),
(['genomics-genetics','evolution'],'population genetics simulator','Population genetics simulation establishes genetic and evolutionary scope.'),
(['ecology','bioimage-analysis'],'ecological objects in airborne imagery','Repository declares ecological computer vision; each notebook needs its own objective evidence.'),
([], 'COPASI','Interface and model-task functions alone are insufficient for a specific biological field.'),
(['physiology'],'models of musculoskeletal structures','Musculoskeletal movement supports physiology and biomechanics.'),
(['pharmacology'],'Drug Repurposing','Drug modeling and screening are explicitly declared.'),
(['transcriptomics'],'genes that are differentially expressed','Lineage analysis alone does not establish a developmental question.'),
([], 'single-cell omics data','Broad omics scope does not resolve which scientific fields apply from this README alone.'),
(['bioimage-analysis'],'tissue images','Image analysis is declared; spatial molecular data alone does not specify transcriptomics.'),
([],None,'Neither bounded root README candidate was acquired.'),
([], 'pairwise sequence alignments','Generic sequence method; a specific biological field is not applicable at this level.'),
(['transcriptomics'],'microarray and RNA-seq data','Expression-based gene-set analysis is explicitly declared.'),
([], 'template for hosting a textbook','Template instructions do not establish scientific scope.'),
([], 'mass and flow cytometry','Cytometry is explicit; a specific immune question is not established in the root README.'),
([],None,'Neither bounded root README candidate was acquired.'),
(['ecology'],'community ecologists','Community and vegetation ecology are explicitly declared.'),
([], 'bookdown','Build instructions do not establish the scientific scope of the book.'),
([], 'base functions for Bioconductor','General software infrastructure has no specific biological field at this level.'),
(['structural-biology','pharmacology'],'Structural Biology','Curriculum explicitly describes structural biology and drug discovery; assignments are selected, not exhaustive.'),
]
cache=json.loads((root/'expanded-repository-content.json').read_text())
assert len(cache)==len(specs)==23
for src,(fields,anchor,rationale) in zip(cache,specs):
 if anchor: assert anchor in src['text'], (src['repo'],anchor)
 status='content_supported' if fields else 'insufficient_evidence'
 if src['repo'] in ['Bioconductor/pwalign','Bioconductor/Biobase']:status='not_applicable'
 if not anchor:status='access_unavailable'
 rows.append(dict(repository=src['repo'],kind='hosting repository',scientific_fields=fields,status=status,source_url=src.get('url'),source_sha256=src.get('sha256'),evidence_anchor=anchor,rationale=rationale,review_scope='Pinned root README only; selected fields, no notebook-to-repository inheritance.',review='assistant_static_iterative_review'))
assert len(rows)==31
(root/'repository-annotations.json').write_text(json.dumps(rows,indent=2)+'\n')
