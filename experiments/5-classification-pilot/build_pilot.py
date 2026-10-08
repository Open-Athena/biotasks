"""Materialize explicit assistant-reviewed pilot annotations, not automatic labels."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sources = {r['id']: r for r in json.loads((ROOT / 'source-content.json').read_text())}
sources.update({r['id']: r for r in json.loads((ROOT / 'extension-source-content.json').read_text())})
repo_sources = {r['repo']: r for r in json.loads((ROOT / 'repository-content.json').read_text())}

def term(label, definition):
    return {'label': label, 'definition': definition}

vocabulary = {
 'version': '0.2-draft',
 'scientific_field': {
  'genomics-genetics': term('Genomics and genetics', 'Genome organization, variation, inheritance and genotype-phenotype relationships; not every operation on sequence files.'),
  'transcriptomics': term('Transcriptomics', 'RNA abundance, expression, splicing and transcript-level analysis.'),
  'epigenomics': term('Epigenomics', 'Chromatin state, accessibility and DNA modification analyses.'),
  'proteomics': term('Proteomics', 'Protein abundance, identification and modification at proteome scale; coordinate analysis alone is structural biology.'),
  'structural-biology': term('Structural biology', 'Molecular structures, conformations and structural dynamics.'),
  'metabolomics': term('Metabolomics', 'Profiles and changes in metabolite measurements; network optimization alone does not establish metabolomics.'),
  'systems-biology': term('Systems biology', 'Mechanistic or network models of interacting biological components.'),
  'microbiome': term('Microbiome science', 'Microbial community composition, diversity and function.'),
  'evolution': term('Evolutionary biology', 'Evolutionary relationships, processes and selection; merely consuming a tree is insufficient.'),
  'ecology': term('Ecology', 'Organism-environment and community ecological questions; not automatically assigned to every microbiome tutorial.'),
  'immunology': term('Immunology', 'Immune populations, repertoires and immune function; immune sample origin alone can remain setting metadata.'),
  'neuroscience': term('Neuroscience', 'Neural signals, organization, activity and function.'),
  'bioimage-analysis': term('Bioimage analysis', 'Biological image-based measurement and characterization. Boundary with cell biology remains under review.'),
  'cell-development': term('Cell and developmental biology', 'Cellular organization, differentiation and developmental processes; single-cell resolution alone is insufficient.'),
  'biochemistry': term('Biochemistry', 'Molecular biochemical mechanisms not adequately described by another assigned field.'),
  'pharmacology': term('Pharmacology and toxicology', 'Drug action, dose response and toxicity.'),
  'epidemiology': term('Epidemiology', 'Population-level disease occurrence, exposures and risk.'),
  'physiology': term('Physiology and biomechanics', 'Organism or organ function and physical mechanics.'),
 },
 'modality': {
  'airr': term('Immune receptor sequencing', 'Adaptive immune receptor sequences and derived clonotypes.'),
  'methylation-array': term('DNA methylation array', 'Probe-level DNA methylation array measurements.'),
  'rgb-image': term('RGB organism images', 'Visible-light organism images; not automatically microscopy.'),
  'scrna': term('Single-cell RNA-seq', 'Cell-resolved RNA sequencing measurements or derived expression matrices.'),
  'bulk-rna': term('Bulk RNA-seq', 'Bulk RNA sequencing measurements or derived expression matrices.'),
  'dna-variants': term('Genotypes and sequence variants', 'Variant/genotype observations; do not infer sequencing versus array assay when unspecified.'),
  'metabolite-profile': term('Metabolite profiles', 'Metabolite measurements; do not infer mass spectrometry versus NMR from a table alone.'),
  'growth': term('Growth measurements', 'Growth or optical-density measurements.'),
  'structure': term('Molecular coordinates', 'Atomic coordinates; experimental or predicted origin is separate metadata.'),
  'trajectory': term('Molecular trajectories', 'Time-indexed molecular coordinates; analysis does not imply running the simulation.'),
  'flow-cytometry': term('Flow cytometry', 'Optical cytometry marker measurements.'),
  'mass-cytometry': term('Mass cytometry', 'Metal-tag cytometry measurements; not inferred solely from tool compatibility.'),
  'microscopy': term('Microscopy', 'Biological microscopy images, with optional optical subtype.'),
  'community-profile': term('Microbial community profiles', 'Taxon abundance and diversity data; amplicon versus shotgun assay may be unspecified.'),
  'electrophysiology': term('Electrophysiology', 'Electrical neural recordings or derived spike/unit tables.'),
  'atac': term('ATAC-seq', 'Chromatin accessibility sequencing.'),
  'chip': term('ChIP-seq', 'Chromatin immunoprecipitation sequencing.'),
  'mass-spectrometry': term('Mass spectrometry', 'Mass-spectral measurements; analyte type described separately.'),
  'spatial-expression': term('Spatial expression profiling', 'Expression observations with spatial registration; retain assay subtype if known.'),
 },
 'operation': {
  'data-access': term('Data access', 'Retrieve or stream supplied data; retrieval alone does not establish biological inference.'),
  'phenotyping': term('Image phenotyping', 'Extract organism/object shape or color measurements from images.'),
  'data-preparation': term('Data preparation', 'Import, subset, transform and reconcile data identities or representations.'),
  'qc': term('Quality assessment and filtering', 'Compute or inspect quality evidence and optionally filter; record whether metrics are supplied.'),
  'normalization': term('Normalization and scaling', 'Adjust measurements for scale or technical effects.'),
  'feature-selection': term('Feature selection', 'Select features by a stated criterion.'),
  'dimension-reduction': term('Dimensionality reduction', 'Compute embeddings or lower-dimensional projections.'),
  'clustering': term('Clustering', 'Infer groups from data; supplied group labels are not sufficient.'),
  'marker-testing': term('Marker testing', 'Compare expression across populations for marker evidence; distinct from replicated treatment inference.'),
  'association': term('Association testing', 'Test genotype-phenotype or other stated associations.'),
  'group-comparison': term('Group comparison', 'Compute group differences or tests; record data provenance and method.'),
  'annotation': term('Biological annotation', 'Assign biological labels or identities using stated evidence.'),
  'structural-comparison': term('Structural comparison', 'Align structures or measure coordinate differences such as RMSD.'),
  'geometry': term('Structural geometry', 'Compute molecular angles, contacts or other geometric descriptors.'),
  'segmentation': term('Image segmentation', 'Partition image content into objects or regions.'),
  'diversity': term('Diversity estimation', 'Compute diversity measures for a specified target, such as communities or immune repertoires.'),
  'descriptive-analysis': term('Descriptive analysis and visualization', 'Summarize or visualize biological observations; not automatically inferential statistics.'),
  'simulation': term('Simulation or mechanistic modeling', 'Generate model outcomes; supplied simulated data do not establish this operation.'),
  'prediction': term('Predictive modeling', 'Fit or apply a predictive model; consuming predictions alone is insufficient.'),
  'integration': term('Data integration', 'Combine datasets/modalities or correct cross-dataset effects.'),
  'alignment': term('Sequence alignment', 'Compute sequence/read alignments; supplied alignments alone are insufficient.'),
  'quantification': term('Quantification', 'Estimate abundances or feature measurements from lower-level observations.'),
  'enrichment': term('Enrichment analysis', 'Test or score sets/pathways against an explicit background or ranking.'),
 },
 'assignment_states': ['suggested', 'content_supported', 'needs_review', 'rejected'],
 'operation_roles': ['implemented', 'exercise', 'discussed_only', 'upstream_supplied'],
 'coverage_rule': 'Count distinct notebook IDs per content-supported label. Operation implemented/exercise counts stay separate; exclude discussed-only/upstream-supplied. Multi-label totals overlap. Static inspection is not execution validation.'
}

rows = []
def add(id, fields, modalities, operations, context_refs, rationale, questions, design, setting, origin, exclusions, tools):
    source = sources[id]
    def evidence(refs):
        valid = {c['locator'] for c in source['chunks']}
        for ref in refs:
            assert ref in valid, (id, ref)
        return refs
    labels = []
    for facet, values in [('scientific_field', fields), ('modality', modalities)]:
        for value in values:
            labels.append({'facet': facet, 'term': value, 'status': 'content_supported',
                           'evidence': evidence(context_refs), 'rationale': rationale})
    for value, role, refs, why in operations:
        labels.append({'facet': 'operation', 'term': value, 'status': 'content_supported',
                       'role': role, 'target': 'document analysis; see rationale', 'evidence': evidence(refs), 'rationale': why})
    rows.append({'id': id, 'title': source['title'], 'hosting_repository': source['repo'],
                 'source_url': source['url'], 'revision': source['revision'], 'source_sha256': source['sha256'],
                 'review': 'assistant_static_pilot', 'independent_review': False, 'executed': False,
                 'labels': labels, 'biological_question': questions, 'design': design, 'setting': setting,
                 'input_origin': origin, 'metadata_evidence': evidence(context_refs),
                 'withheld_labels': exclusions, 'tools_used': tools,
                 'scope': 'Whole document; targeted narrative/code evidence reviewed. Operation list is not exhaustive.'})

add('G01',['structural-biology'],['structure'],[
 ('geometry','implemented',['cell:17','cell:18'],'Computes backbone dihedral angles.'),
 ('descriptive-analysis','implemented',['cell:4','cell:20'],'Displays coordinates and angle scatter plot.')],
 ['cell:0','cell:3','cell:13','cell:17'], 'AlphaFold coordinates are downloaded and analyzed, not predicted locally.',
 None, [], [], 'predicted coordinates', ['Protein prediction is upstream supplied; no proteome-scale measurement.'], ['Gemmi','Biopython','py3Dmol'])
add('G02',['systems-biology','metabolomics'],['metabolite-profile','growth'],[
 ('descriptive-analysis','implemented',['cell:14','cell:43','cell:45'],'Ranks growth measurements and plots strain concentration differences.'),
 ('simulation','exercise',['cell:5','cell:7','cell:8','cell:9'],'An external Escher-FBA exercise asks learners to perturb reactions; no local FBA solver call.')],
 ['cell:0','cell:12','cell:19','cell:25'], 'Metabolic network exercises and measured metabolite/growth comparisons address engineered E. coli.',
 'How engineering changes growth and metabolite profiles', ['perturbational','time-course'], ['E. coli'],
 'mixed: source-described measured data plus model exercise', ['No mass-spectrometry assay inferred from metabolite concentrations.'], ['pandas','Escher (external exercise)'])
add('E01',['transcriptomics'],['scrna'],[
 ('qc','implemented',['line:150','line:237'],'Computes QC metrics and filters cells.'),
 ('normalization','implemented',['line:275','line:276'],'Normalizes totals and log transforms.'),
 ('feature-selection','implemented',['line:278'],'Selects highly variable genes.'),
 ('dimension-reduction','implemented',['line:341','line:401'],'Computes PCA and UMAP.'),
 ('clustering','implemented',['line:402'],'Runs Leiden clustering.'),
 ('marker-testing','implemented',['line:459','line:460'],'Runs cluster marker tests.')],
 ['line:102','line:111','line:459','line:460'], 'PBMC single-cell expression analysis with computed clusters and marker testing.',
 'Characterize expression-defined cell populations', [], ['PBMC'], 'source-described observed PBMC3k',
 ['No replicated treatment differential-expression analysis; immune cell origin alone does not force immunology.'], ['Scanpy','Polars','Plotnine'])
add('E05',['genomics-genetics'],['dna-variants'],[
 ('dimension-reduction','exercise',['line:241','line:244','line:245','line:250'],'PCA code is supplied in an eval:false teaching block; rendered path loads precomputed PCA.'),
 ('association','exercise',['line:599','line:603','line:605','line:611','line:613'],'GWAS is requested in learner instructions rather than an implemented run call.'),
 ('data-preparation','implemented',['line:77','line:78','line:152'],'Reads genotype identifiers and accession metadata.')],
 ['line:10','line:38','line:56','line:579'], 'Arabidopsis genotype and flowering-time data support an association exercise.',
 'Genetic associations with flowering time', [], ['Arabidopsis thaliana'], 'source-described observed panel',
 ['Do not claim a completed GWAS or default PCA execution from headings.'], ['rhdf5','stats','statgenGWAS (exercise)'])
add('E09',['immunology'],['flow-cytometry'],[
 ('normalization','implemented',['line:73','line:74','line:77','line:78'],'Compensates and transforms optical cytometry measurements.'),
 ('clustering','implemented',['line:93','line:101'],'Fits FlowSOM and metaclusters.'),
 ('annotation','implemented',['line:247','line:248','line:330','line:332'],'Uses immune-cell labels and a CD8 marker query.'),
 ('group-comparison','implemented',['line:359','line:364','line:368','line:382','line:383'],'Compares groups generated by resampling a cytometry file.')],
 ['line:69','line:73','line:247','line:248','line:359','line:360'], 'Optical compensation and immune-cell labels support flow cytometry and immunology; CyTOF is only discussed.',
 'Identify immune populations and illustrate abundance differences', ['synthetic group contrast'], ['immune cells'],
 'mixed: supplied FCS plus synthetic resampling', ['No observed case-control study; no mass-cytometry demonstration inferred from compatibility.'], ['FlowSOM','flowCore','flowWorkspace'])
add('A04',['bioimage-analysis'],['microscopy'],[
 ('segmentation','implemented',['line:555','line:699','line:702'],'Watershed and threshold/connected-component segmentation on nuclei images.'),
 ('descriptive-analysis','implemented',['line:691','line:692','line:719'],'Displays cell images and object overlays.')],
 ['line:7','line:683','line:685','line:688','line:689'], 'Fluorescent cell/nucleus examples support image analysis; no disease mechanism established.',
 None, [], ['cells; organism unspecified'], 'sample images; biological provenance not independently checked',
 ['No cancer or cell-development question inferred from generic cell images.'], ['EBImage'])
add('L09',['structural-biology'],['trajectory','structure'],[
 ('structural-comparison','implemented',['cell:8','cell:12','cell:25'],'Aligns structures and computes RMSD over a supplied trajectory.'),
 ('descriptive-analysis','implemented',['cell:17','cell:18'],'Summarizes RMSD over frames.')],
 ['cell:4','cell:8','cell:12'], 'AdK structure/trajectory comparison uses supplied files.',
 'Compare adenylate kinase conformations', [], ['adenylate kinase'], 'supplied molecular-dynamics trajectory and reference coordinates',
 ['No simulation execution; no organism inferred.'], ['MDAnalysis'])
add('L14',['structural-biology'],['trajectory'],[
 ('structural-comparison','implemented',['cell:6'],'Aligns trajectory frames.'),
 ('dimension-reduction','implemented',['cell:8','cell:17'],'Fits and applies PCA to coordinate trajectories.'),
 ('qc','implemented',['cell:30','cell:31'],'Computes cosine content to assess sampling/convergence.')],
 ['cell:2','cell:3','cell:8'], 'Analyzes adenylate kinase trajectory conformation using PCA.',
 'Characterize conformational motions', [], ['adenylate kinase'], 'supplied molecular-dynamics trajectory',
 ['No simulation execution; PCA alone does not establish transcriptomics.'], ['MDAnalysis'])
add('L28',['microbiome'],['community-profile'],[
 ('diversity','implemented',['line:423','line:424','line:426'],'Computes alpha diversity for a supplied community dataset.'),
 ('descriptive-analysis','implemented',['line:428','line:429'],'Plots diversity by supplied patient status.')],
 ['line:260','line:271','line:423','line:424','line:428'], 'Community-diversity teaching includes random trees and a patient-status example.',
 'Summarize within-sample community diversity', [], [], 'mixed: random tree plus packaged community example',
 ['No sequencing assay, disease or observed case-control design inferred without dataset provenance; tree use does not imply phylogenetic inference.'], ['mia','miaViz','ape'])
add('L17',['neuroscience'],['electrophysiology'],[
 ('qc','implemented',['cell:10','cell:17','cell:20','cell:22'],'Inspects supplied unit quality measures rather than computing spike sorting.'),
 ('descriptive-analysis','implemented',['cell:17','cell:25'],'Plots unit metrics and spike amplitudes.')],
 ['cell:2','cell:7','cell:8','cell:10'], 'Neuropixels/NWB unit metrics support neural recording QC.',
 'Assess neural unit quality', [], ['neural units'], 'source-described observed recording; derived metrics supplied',
 ['Spike sorting, waveform PCA and discrimination are upstream; explanations do not establish implementation.'], ['OpenScope databook utilities','NWB','DANDI','NumPy'])


add('G04',['genomics-genetics'],['dna-variants'],[
 ('data-access','implemented',['cell:2','cell:5','cell:6','cell:7'],'Downloads a supplied VCF and index from blob storage.'),
 ('descriptive-analysis','implemented',['cell:8','cell:10'],'Displays supplied variant tracks in IGV.')],
 ['cell:0','cell:2','cell:10'], 'Genomic variants are the subject of a cloud access/display demonstration, not variant calling.',
 None, [], ['human hg38 reference'], 'supplied example VCF; provenance not independently checked',
 ['No variant calling, association testing or clinical interpretation.'], ['Azure Blob Storage','IGV'])
add('L25',['immunology','transcriptomics'],['airr','scrna'],[
 ('normalization','implemented',['cell:12'],'Normalizes supplied expression measurements.'),
 ('dimension-reduction','implemented',['cell:12'],'Computes expression PCA.'),
 ('dimension-reduction','upstream_supplied',['cell:13','cell:14'],'Uses supplied expression UMAP coordinates.'),
 ('clustering','upstream_supplied',['cell:13','cell:15'],'Uses supplied gene-expression clusters.'),
 ('clustering','implemented',['cell:51','cell:52'],'Computes receptor clonotype clusters from CDR3 similarity.'),
 ('qc','implemented',['cell:25','cell:33','cell:35'],'Assesses receptor chains and filters chain configurations.'),
 ('marker-testing','implemented',['cell:133'],'Tests expression markers between clonotypes.'),
 ('annotation','implemented',['cell:138','cell:140','cell:142'],'Queries reference receptor sequences for epitope annotations.')],
 ['cell:4','cell:8','cell:12','cell:39','cell:43'], 'The same notebook analyzes gene expression and receptor clonotypes; both field labels have direct content evidence.',
 'Characterize T-cell clonotypes and their expression in cancer samples', [], ['T cells','cancer'],
 'adapted subset of source-described observed single-cell data',
 ['Do not attribute implemented expression clustering or UMAP from supplied coordinates; clonotype clustering is a distinct target.'], ['Scirpy','Scanpy','MuData'])
add('L40',['epigenomics'],['methylation-array'],[
 ('data-preparation','implemented',['line:125','line:140','line:147'],'Reads methylation-array sample sheets and intensities.'),
 ('qc','discussed_only',['line:204','line:206','line:208'],'Quality-control section is a list of suggestions, not implemented analysis.'),
 ('normalization','discussed_only',['line:214','line:220','line:221','line:223'],'Lists normalization methods; no normalization call is implemented here.'),
 ('group-comparison','discussed_only',['line:235','line:237','line:238'],'Differential methylation section lists methods only.')],
 ['line:23','line:25','line:125','line:140'], 'Array introduction supports epigenomics and methylation-array modality; a method inventory is not implementation coverage.',
 None, [], [], 'packaged example intensities; biological provenance not independently checked',
 ['No implemented normalization, differential methylation or cell-composition estimation inferred from headings.'], ['minfi'])
add('L01',['bioimage-analysis'],['rgb-image'],[
 ('segmentation','implemented',['cell:19','cell:21','cell:25'],'Thresholds and filters the plant mask.'),
 ('phenotyping','implemented',['cell:28','cell:29'],'Extracts shape and color measurements from a whole-plant image.')],
 ['cell:0','cell:4','cell:9','cell:28'], 'Whole-plant image analysis supports bioimage analysis without implying cellular imaging or developmental inference.',
 'Measure plant shape and color', [], ['plant'], 'supplied RGB image; biological provenance not independently checked',
 ['Not microscopy; no cell biology or developmental process inferred from segmentation alone.'], ['PlantCV'])

for r in rows:
    r['annotation_version'] = '0.2-draft'
    r['reviewed_date'] = '2026-10-08'
    r['source_role'] = 'infrastructure_demonstration' if r['id']=='G04' else 'analysis_or_teaching_document'
    r['facet_review'] = {f: 'content_supported' if any(a['facet']==f for a in r['labels']) else 'insufficient_evidence' for f in ['scientific_field','modality','operation']}
    if r['id']=='L25':
        targets={('normalization','implemented'):'gene expression',('dimension-reduction','implemented'):'gene-expression PCA',('dimension-reduction','upstream_supplied'):'gene-expression UMAP',('clustering','upstream_supplied'):'gene-expression cell populations',('clustering','implemented'):'receptor clonotypes',('qc','implemented'):'receptor chain configurations',('marker-testing','implemented'):'expression across clonotypes',('annotation','implemented'):'receptor epitope matching'}
        for a in r['labels']:
            if a['facet']=='operation': a['target']=targets[(a['term'],a['role'])]

repo_specs = {
 'Brunk-Lab/Digital-Upskilling-BioScience': (['structural-biology','metabolomics','transcriptomics','proteomics','epigenomics'], 'curriculum', 'Levels Overview', 'Broad curriculum explicitly lists several omics areas; individual notebooks need not cover them all.'),
 'wolf5996/scanpy-done-right': (['transcriptomics'], 'tutorial', 'single-cell RNA-seq', 'README describes a PBMC expression workflow; its DEA exclusion requires a distinction between marker testing and treatment inference.'),
 'wur-bioinformatics/exploratory-data-analysis': ([], 'teaching collection', 'Exploratory Data Analysis', 'Root README is insufficient for biological scope; do not backfill from the selected notebook.'),
 'saeyslab/FlowSOM': ([], 'tool', 'cytometry data', 'README establishes cytometry but does not establish a specific biological field independently.'),
 'aoles/EBImage': ([], 'tool', 'Documentation', 'Root README points elsewhere for functionality; biological field scope remains unclassified in this bounded README pass.'),
 'MDAnalysis/UserGuide': (['structural-biology'], 'documentation collection', 'molecular dynamics files and trajectories', 'Declared molecular-trajectory analysis scope; this is the documentation host, not the toolkit source repository.'),
 'microbiome/outreach': ([], 'outreach collection', 'miaverse', 'Project name alone is insufficient independent scope evidence in this README-only pass.'),
 'AllenInstitute/openscope_databook': (['neuroscience'], 'documentation collection', 'brain data analysis', 'README declares brain analysis and multiple neural recording/imaging tutorials.')
}
repos = []
for repo, (fields, kind, anchor, rationale) in repo_specs.items():
    src = repo_sources[repo]
    assert anchor in src['text']
    repos.append({'repository': repo, 'kind': kind, 'scientific_fields': fields,
                  'status': 'content_supported' if fields else 'insufficient_evidence',
                  'source_url': src['url'], 'source_sha256': src['sha256'], 'evidence_anchor': anchor,
                  'rationale': rationale, 'review_scope': 'Pinned root README only; no notebook-to-repository inheritance.',
                  'review': 'assistant_static_pilot'})

for source in json.loads((ROOT / 'extension-sample.json').read_text()):
    repos.append({'repository': source['repo'], 'kind': 'unreviewed', 'scientific_fields': [], 'status': 'unreviewed', 'review_scope': 'Notebook inspected; repository scope not inspected in this extension.'})

for facet in ['scientific_field','modality','operation']:
    used = {a['term'] for r in rows for a in r['labels'] if a['facet'] == facet}
    for key, t in vocabulary[facet].items():
        t['pilot_status'] = 'exercised_in_sample' if key in used else 'proposed_not_tested'
for name, data in [('vocabulary.json',vocabulary),('annotations.json',rows),('repository-annotations.json',repos)]:
    (ROOT / name).write_text(json.dumps(data,indent=2)+'\n')

# Validate structure and evidence locators, not the correctness of biological judgments.
assert len(rows) == 14 and len({r['id'] for r in rows}) == 14
assert len(repos) == 12
for row in rows:
    for label in row['labels']:
        assert label['term'] in vocabulary[label['facet']]
        assert label['evidence']
        if label['facet']=='operation': assert label['role'] in vocabulary['operation_roles']
assert not any(a['term']=='clustering' for a in next(r for r in rows if r['id']=='L17')['labels'])
assert all(a['role']=='exercise' for a in next(r for r in rows if r['id']=='E05')['labels'] if a['term'] in ['association','dimension-reduction'])
counts = {facet: {key: len({r['id'] for r in rows if any(a['facet']==facet and a['term']==key and (facet!='operation' or a['role']=='implemented') for a in r['labels'])}) for key in vocabulary[facet]} for facet in ['scientific_field','modality','operation']}
(ROOT/'validation.json').write_text(json.dumps({'passed':True,'scope':'Structural checks only; no independent semantic review or execution', 'documents':len(rows),'repositories':len(repos),'repository_readmes_reviewed':8,'repository_fields_supported':sum(bool(r['scientific_fields']) for r in repos),'counts':counts},indent=2)+'\n')

lines=['# Notebook classification pilot: draft for discussion','',
'Fourteen purposively selected documents from twelve hosting repositories were statically inspected at pinned revisions. Formats include Jupyter, marimo, Quarto, R Markdown and Sweave. The sample tests distinctions and failure cases; it is not representative and provides no population coverage estimate. The published inventory and inherited labels are unchanged.','',
'## Sample assignments','',
'| Source | Scientific fields | Modality/data type | Selected operations |',
'| --- | --- | --- | --- |']
for r in rows:
    def fmt(f):
        return ', '.join(vocabulary[f][a['term']]['label'] + (' [' + a['target'] + ']' if r['id']=='L25' and f=='operation' else '') + (' (' + a['role'].replace('_',' ') + ')' if a.get('role') and a['role']!='implemented' else '') for a in r['labels'] if a['facet']==f)
    lines.append(f"| [{r['id']}: {r['title']}]({r['source_url']}) | {fmt('scientific_field')} | {fmt('modality')} | {fmt('operation')} |")
lines += ['', '## What the pilot changes', '',
'1. **Operation role matters.** The Arabidopsis GWAS is a learner exercise, with no implemented GWAS call. Its PCA teaching block is disabled for rendering and replaced by precomputed results. The metabolic tutorial similarly sends learners to an external FBA tool. Report exercises separately from implemented operations.',
'2. **Upstream work must not leak into coverage.** Neural quality-metric plots do not run spike sorting; molecular trajectory analysis does not run dynamics; downloading an AlphaFold structure does not perform structure prediction.',
'3. **Data modality cannot always mean assay.** Predicted structures, trajectories and derived community tables are meaningful inputs. Call this facet “Data modality,” retain the original assay separately when evidenced, and track observed/adapted/simulated/predicted/mixed origin.',
'4. **A method name can hide different scientific questions.** Scanpy marker tests characterize clusters; they do not establish replicated treatment-effect inference. Its README excludes differential expression while its code runs marker tests: preserve the scope distinction rather than erasing either evidence.',
'5. **Repository scope is not notebook scope.** The Brunk curriculum declares multiple omics areas; its structure notebook does not inherit transcriptomics or metabolomics. The two MDAnalysis examples share a field/modality but have different operations. Four of eight root READMEs support field assignments in this bounded pass; four remain insufficient, even though their sampled notebook contents support labels.',
'6. **Cross-cutting fields need conservative rules.** Immune origin alone is setting metadata for PBMC expression analysis; explicit immune-population identification supports immunology for FlowSOM. The v0.2 working rules use the analysis objective to distinguish field from setting. Bioimage analysis remains a browse field; generic masks do not imply cell/developmental biology. These are provisional reviewer judgments, not an independently validated taxonomy.',
'', '## Evidence and status', '',
'[Readable vocabulary](vocabulary.md) and [machine-readable vocabulary](vocabulary.json) give stable IDs, definitions and whether each term was exercised in this sample. Untested terms are proposals, not an established ontology. [Notebook annotations](annotations.json) retain field-specific evidence locators, operation roles, withheld labels and provenance. [Repository annotations](repository-annotations.json) use separate README evidence. [Validation](validation.json) checks IDs, vocabulary membership, evidence locators and count arithmetic, not biological correctness.',
'',
'All fourteen selected documents have pilot annotations. Eight hosting READMEs were inspected separately; the four extension hosts remain unreviewed at repository level. This says nothing about the classified fraction of the 4,277-document inventory: the sample comes from the separate historical 100-candidate screening collection, and has not been joined to the full registry. Zero additional corpus-wide labels were applied. Assignment review is assistant static inspection, with no independent human review and no notebook execution. Operations listed are selected, not exhaustive.',
'',
'`source-content.json`, `extension-source-content.json` and `repository-content.json` are local inspection caches containing upstream text, retained for review but not published. Acquisition records preserve pinned URLs and hashes. Notebook cell locators are zero-based; text line locators are one-based. No biological inputs or source analyses were downloaded/executed. Only source documents and root READMEs were fetched.',
'', '## Extension findings', '',
'The immune-repertoire notebook supports both Immunology and Transcriptomics. It computes receptor clonotype clusters while consuming precomputed expression clusters, so every operation assignment now has an explicit target or a rationale identifying it. Its supplied UMAP and computed PCA also need different roles. The minfi source lists normalization and differential methylation without implementing them. The PlantCV source measures a whole plant, supporting RGB imaging rather than microscopy or cellular biology. The Azure notebook supports a Genomics context but its role is infrastructure demonstration: access and visualization, not variant calling.', '',
'The plant source was newly pinned from a formerly floating link; the extension source record preserves its resolved revision. This pilot does not reclassify the earlier frozen snapshot. The immune notebook required a verified 8 MiB cap because of embedded outputs, which are excluded from the local inspection text. The initial cap failure and lock stop are recorded.', '',
'## Proposed next decisions', '',
'- Keep the field/modality/operation scheme, with operation roles and input origin added as demonstrated by this pilot.',
'- The [v0.2 rules](decisions.md) resolve the pilot boundaries provisionally; review them against the contrasting Scirpy, PBMC, EBImage and PlantCV examples.',
'- Before scaling, add contrasting cases for the untested fields and general infrastructure, and independently review disagreements. Do not infer broad field coverage from this purposive sample.',
'- The current vocabulary has 18 candidate fields, not a mutually exclusive partition. Report notebook counts by distinct ID and show overlaps; do not sum field counts as a corpus total.',
'']
(ROOT/'README.md').write_text('\n'.join(lines))
print('Built 14 notebook annotations, 12 repository records (8 README-reviewed, 4 unreviewed) and structural validation.')
