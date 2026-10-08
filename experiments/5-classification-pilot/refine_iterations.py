"""Explicit source-reviewed iterations; does not execute or automatically classify notebooks."""
import json
from pathlib import Path
from collections import Counter

ROOT=Path(__file__).resolve().parent
v=json.loads((ROOT/'vocabulary.json').read_text())
# Idempotent after the original builder or a previous refinement run.
base_ids={r['id'] for f in ['sample.json','extension-sample.json'] for r in json.loads((ROOT/f).read_text())}
rows=[r for r in json.loads((ROOT/'annotations.json').read_text()) if r['id'] in base_ids]
sources={r['id']:r for f in ['source-content.json','extension-source-content.json','round3-source-content.json','round4-source-content.json','challenge-source-content.json'] for r in json.loads((ROOT/f).read_text())}
def term(label,definition): return {'label':label,'definition':definition}
v['version']='0.3-working'
v['operation'].update({
 'model-construction':term('Mechanistic model construction','Define reactions, equations, parameters or constraints; distinguish specification from running simulations.'),
 'inverse-modeling':term('Inverse modeling','Infer physical states, forces or parameters from observations with a forward model.'),
 'statistical-modeling':term('Statistical model fitting','Fit a statistical model for a stated inferential target; fitting alone does not establish predictive validation.'),
 'spatial-statistics':term('Spatial statistics','Compute spatial organization, autocorrelation or neighborhood statistics; not gene-set enrichment.'),
})
v['operation']['simulation']['definition']='Run a mechanistic or stochastic model to generate outcomes; model construction and supplied simulations are separate.'
v['modality'].update({
 'sequences':term('Biological sequences','Nucleotide or amino-acid sequences; record molecule subtype and source when known.'),
 'ancestral-trees':term('Ancestral trees and tree sequences','Ancestral relationships along genomes, including simulated genealogies.'),
 'model-data':term('Model specifications and parameters','Equations, reaction schemes, parameters or initial conditions; a model input, not an experimental assay.'),
 'motion-force':term('Motion capture and forces','Body-marker trajectories and force measurements for biomechanical inference.'),
 'chemical-assay':term('Molecular structures and bioassay outcomes','Chemical representations paired with activity outcomes; do not infer clinical efficacy.'),
 'community-vegetation':term('Community species and environment tables','Species/community observations with environmental covariates.'),
 'protein-profile':term('Protein abundance profiles','Derived protein measurements; underlying assay must be separately evidenced.'),
})
v['modality']['rgb-image']['label']='RGB organism or habitat images'
v['modality']['rgb-image']['definition']='Visible-light organism or habitat images; not automatically microscopy or ecological inference.'
v['scientific_field']['bioimage-analysis']['definition']='Image-based biological detection, measurement and characterization; cell biology or ecology needs additional objective/interpretation evidence.'
v['scientific_field']['immunology']['definition']='Immune populations, repertoires or function as an analytical subject; immune sample origin alone remains setting metadata.'
v['facet_states']=['unreviewed','content_supported','insufficient_evidence','not_applicable','disputed']
v['source_roles']=['analysis_or_teaching_document','infrastructure_demonstration','tool_development','navigation_stub','generic_method_demonstration']

def ev(id,*needles):
    out=[]
    for needle in needles:
        matches=[c['locator'] for c in sources[id]['chunks'] if needle in c['text']]
        assert matches,(id,needle)
        out.append(matches[0])
    return list(dict.fromkeys(out))

def add(id, fields, modalities, operations, context, rationale, origin, question=None, setting=None, role='analysis_or_teaching_document', withheld=None, notes=None, design=None):
    src=sources[id]; refs=ev(id,*context)
    labels=[]
    for facet,terms in [('scientific_field',fields),('modality',modalities)]:
        for t in terms: labels.append({'facet':facet,'term':t,'status':'content_supported','evidence':refs,'rationale':rationale})
    for t,role_op,target,needles,why in operations:
        labels.append({'facet':'operation','term':t,'status':'content_supported','role':role_op,'target':target,'evidence':ev(id,*needles),'rationale':why})
    rows.append({'id':id,'title':src['title'],'hosting_repository':src['repo'],'source_url':src['url'],'revision':src['revision'],'source_sha256':src['sha256'],'review':'assistant_static_iterative_review','independent_review':False,'executed':False,'labels':labels,'source_role':role,'facet_review':{f:'content_supported' if any(a['facet']==f for a in labels) else 'not_applicable' if role in ['tool_development','navigation_stub','generic_method_demonstration'] else 'insufficient_evidence' for f in ['scientific_field','modality','operation']},'biological_question':question,'design':design or [],'setting':setting or [],'input_origin':origin,'metadata_evidence':refs,'withheld_labels':withheld or [],'review_notes':notes or [],'tools_used':[],'annotation_version':v['version'],'reviewed_date':'2026-10-08','scope':'Selected operations; static source evidence, not exhaustive execution review.'})

def op(t,target,needles,why,role='implemented'):return (t,role,target,needles,why)
add('N01',['proteomics'],['mass-spectrometry'],[
 op('quantification','reporter-ion abundance',['qnt <- quantify(experiment'],'Computes reporter-ion quantification from spectra.'),
 op('normalization','quantitative protein measurements',['qnt.quant <- normalise'],'Applies quantile normalization.')],
 ['proteomics data analysis','proteomics mass spectrometry'], 'Spectral processing and reporter quantification directly support proteomics.', 'mixed package spectra and demonstrations; original studies not independently reviewed')
add('N02',['evolution','genomics-genetics'],['ancestral-trees','model-data'],[
 op('simulation','ancestral tree sequences',['ts = msprime.sim_ancestry(2, random_seed=1234)'],'Runs coalescent ancestry simulation.')],
 ['Ancestry simulations','coalescent units'], 'Ancestry, recombination and demography are modeled explicitly.', 'simulated', question='How ancestry changes under demographic and genome models',withheld=['No observed sequence dataset or mutation simulation inferred solely from ancestry simulation.'])
add('N03',['bioimage-analysis'],['rgb-image'],[
 op('prediction','nest detector training',['m.trainer.fit(m)'],'Fits an object detector.'),
 op('prediction','nest detector evaluation',['results = m.evaluate('],'Evaluates a detector against annotated boxes.')],
 ['nest detection model','label_dict','nest_data.csv'], 'This document trains an image detector; a broader ecological inference is not demonstrated.', 'annotated image dataset; acquisition provenance not independently reviewed', setting=['bird nests'],withheld=['Ecology is a candidate repository scope, not established here by the image subject alone.'],notes=['Training configuration requests GPUs; source was not executed. Final prediction path is an empty user placeholder.'])
add('N04',['biochemistry','systems-biology'],['model-data'],[
 op('model-construction','reaction kinetics',['add_reaction(\'R1\', \'A -> B\')','Allosteric inhibition (MWC)'],'Defines and modifies reaction laws with inhibitors.')],
 ['Editing reaction kinetics','Allosteric inhibition (MWC)'], 'Allosteric kinetic specification is biochemical model construction.', 'toy model specification',withheld=['No time-course simulation call is present in the reviewed workflow.'])
add('N05',['physiology'],['motion-force','model-data'],[
 op('inverse-modeling','joint motion',['inverse_kinematics_tool.run()'],'Solves inverse kinematics from marker data.'),
 op('inverse-modeling','joint forces and moments',['inverse_dynamics_tool.run()'],'Solves inverse dynamics.'),
 op('model-construction','subject-scaled musculoskeletal model',['scale_tool.run()'],'Scales the generic model for the subject.')],
 ['Inverse Kinematics computes','musculoskeletal model'], 'Body motion and inverse dynamics directly support biomechanics.', 'supplied model plus source-described experimental marker/force data',question='Infer subject motion and joint loads',withheld=['Scaling a physical model is not expression normalization.'])
add('N06',['pharmacology'],['chemical-assay'],[
 op('prediction','compound activity',['model.train(train, val, test)','y_pred = model.predict(X_pred)'],'Trains and applies activity prediction.')],
 ['dataset.load_HIV','CompoundPred.repurpose'], 'Compound activity and antiviral repurposing are pharmacological prediction demonstrations.', 'mixed bioassay/toy inputs and candidate compounds',withheld=['No clinical efficacy or epidemiological analysis inferred from an HIV assay.'])
add('N07',['transcriptomics','cell-development'],['scrna'],[
 op('statistical-modeling','expression over pseudotime',['sce <- fitGAM(counts = counts'],'Fits gene-wise smoothers.'),
 op('association','expression versus pseudotime',['assoRes <- associationTest(sce)'],'Tests expression dependence on pseudotime.'),
 op('group-comparison','lineage start/end expression',['startRes <- startVsEndTest(sce)'],'Tests lineage endpoint contrasts.')],
 ['single-cell RNA-sequencing','progenitor cell population','differentiated cell'], 'Differentiation questions are explicit, not merely implied by single-cell inputs.', 'adapted source-described single-cell data with supplied trajectories',question='How expression changes across differentiation',withheld=['Supplied trajectory objects do not establish de novo trajectory inference.'])
add('N08',['epigenomics'],['atac'],[
 op('dimension-reduction','chromatin latent representation',['model.get_latent_representation()'],'Extracts a fitted PeakVI latent representation.'),
 op('clustering','chromatin-defined cells',['sc.tl.leiden('],'Computes latent-space clusters.'),
 op('group-comparison','chromatin accessibility',['model.differential_accessibility('],'Compares cluster accessibility.')],
 ['scATACseq','already preprocessed dataset'], 'Chromatin accessibility and differential accessibility support epigenomics.', 'supplied preprocessed PBMC ATAC data',setting=['PBMC'],withheld=['No enrichment execution inferred from the closing suggestion to use enrichment methods.'])
add('N10',['transcriptomics','cell-development'],['spatial-expression'],[
 op('spatial-statistics','cell neighborhoods',['sq.gr.nhood_enrichment('],'Computes spatial neighborhood enrichment, not gene-set enrichment.'),
 op('spatial-statistics','cell-type point patterns',['sq.gr.ripley('],'Computes point-pattern statistics.'),
 op('spatial-statistics','gene expression autocorrelation',['sq.gr.spatial_autocorr('],'Computes Moran autocorrelation.')],
 ['Slide-seqV2','cellular organization and communication'], 'Spatial expression and cellular organization are explicit analytical subjects.', 'preprocessed subset with supplied clusters',withheld=['No computed cell clustering inferred from supplied cluster annotations.'])
add('N11',['transcriptomics'],['bulk-rna'],[
 op('group-comparison','RNA expression under perturbation',['dds <- DESeq(dds)'],'Fits the DESeq2 differential-expression workflow.')],
 ['Analyzing RNA-seq','RNAi knock-down'], 'The pasilla example compares expression after an RNA perturbation.', 'source-described observed count data plus additional illustrative examples',design=['perturbational'],withheld=['Single-cell recommendations do not turn this selected bulk example into executed single-cell analysis.'])
add('N12',[],['sequences'],[
 op('alignment','protein sequences',['pairwiseAlignment(AAString('],'Computes protein sequence alignment with a substitution matrix.')],
 ['pairwiseAlignment(AAString(','DNAString('], 'Generic sequence-method documentation need not be forced into a biological field.', 'mixed toy strings, biological sequence examples and simulations',role='generic_method_demonstration',withheld=['A substitution matrix with evolutionary motivation does not establish an evolutionary analysis.'])
add('N13',['proteomics','transcriptomics'],['protein-profile','bulk-rna'],[
 op('enrichment','gene-set scores',['es_gsva_everything <- gsva(gsvapar)','es_gsva <- gsva(gsvapar)'],'Scores gene sets on expression/protein matrices, including missing-data comparisons.')],
 ['GSVA on proteomics','normalized log-CPM RNA-seq'], 'Both RNA and protein matrices are processed; field labels follow content rather than title.', 'source-derived profiles with artificial missingness and imputation comparisons',withheld=['Scoring supplied sets does not establish biological pathway activation as ground truth.'])
add('N14',['epidemiology'],['model-data'],[
 op('simulation','SIR population dynamics',['sir_sol = solve_ivp('],'Integrates a specified SIR model.')],
 ['def sir_ode','dS = -b*S*I'], 'SIR susceptible/infected/recovered dynamics is a mathematical epidemiology example.', 'simulated',withheld=['No observed epidemic data or fitted disease parameters.'])
add('C01',['immunology'],['mass-cytometry'],[
 op('clustering','cytometry-defined immune populations',['sce <- cluster(sce'],'Computes cytometry clusters.'),
 op('data-preparation','mass-cytometry measurements',['sce <- prepData(fs'],'Builds the analysis object from FCS and sample metadata.')],
 ['subset of CyTOF data','Bodenmiller_BCR_XL_flowSet','BCR/FcR-XL stimulation'], 'The actual example uses mass cytometry with immune stimulation.', 'adapted observed paired donor data',design=['paired','perturbational'],withheld=['Flow cytometry is described as compatible; the selected example is CyTOF.'])
add('C02',['epigenomics'],[],[],['guide has been migrated'], 'A migration notice describes a topic but contains no substantive analysis.', 'not applicable',role='navigation_stub',withheld=['No ChIP-seq data processing inferred from the wrapper title.'],notes=['Followed the migration to C05; these are distinct source files, not two independent analysis examples.'])
add('C03',['ecology'],['community-vegetation'],[
 op('dimension-reduction','community ordination',['ord <- metaMDS(dune'],'Computes community ordination.'),
 op('association','community/environment association',['ord.fit <- envfit('],'Fits environmental covariates.'),
 op('statistical-modeling','constrained community ordination',['ord <- cca(dune ~ A1 + Management'],'Models community composition using environmental covariates.')],
 ['community ecologists','vegetation ordination','data(dune.env)'], 'Species and environmental analyses directly address community ecology.', 'packaged vegetation/environment data',question='How vegetation composition relates to environmental variables')
add('C04',['transcriptomics'],['scrna'],[
 op('integration','lung expression batches',['batch_key="batch"','model.train()'],'Fits scVI conditioned on batch.'),
 op('dimension-reduction','integrated expression representation',['model.get_latent_representation()'],'Extracts learned coordinates.'),
 op('clustering','integrated cell populations',['sc.tl.leiden(adata)'],'Clusters the integrated representation.')],
 ['Atlas-level integration of lung data','preprocessed dataset'], 'RNA sample integration is explicit.', 'preprocessed lung atlas data',setting=['lung'],withheld=['Benchmarking cell labels does not independently validate biological identities.'])
add('C05',['epigenomics'],['chip'],[
 op('quantification','ChIP genomic windows',['win.data <- windowCounts('],'Counts reads in genomic windows.'),
 op('statistical-modeling','window count dispersion',['fit <- glmQLFit('],'Fits a quasi-likelihood count model.'),
 op('group-comparison','H3K9ac binding',['res <- glmQLFTest('],'Tests a pro-B/mature-B contrast.')],
 ['differential H3K9ac enrichment','window-based differential binding'], 'The migrated chapter implements a substantive ChIP-seq comparison.', 'source-described observed BAMs with derived window counts',setting=['pro-B cells','mature B cells'],withheld=['Read alignment is supplied upstream.'])
add('H01',[],[],[],['strategies that developers','Implementing a new class'], 'Software class development is not a biological analysis merely because its objects can hold assays.', 'not applicable',role='tool_development',withheld=['No Transcriptomics label inherited from ExpressionSet naming.'])
add('H02',['transcriptomics'],['bulk-rna'],[
 op('group-comparison','simulated expression groups',['from scipy.stats import ttest_ind'],'Implements an illustrative t-test comparison, not DESeq2.'),
 op('normalization','simulated expression counts',['def cpm(count_matrix)'],'Implements CPM normalization.')],
 ['Simulate','RNA-seq'], 'Synthetic RNA-count examples retain transcriptomics context with simulated provenance.', 'simulated; real-data section is an exercise',withheld=['No observed RNA-seq study or DESeq2 execution inferred from teaching prose.'],notes=['Worked incorrect-code exercises coexist with answers; implementation labels are not correctness endorsement.'])
add('H03',['structural-biology'],['trajectory'],[
 op('geometry','native contacts',['contacts.Contacts(u,'],'Computes contact fractions from a supplied trajectory.')],
 ['Fraction of native contacts','mda.Universe(PSF, DCD)'], 'Protein contact geometry is analyzed from provided coordinates.', 'supplied molecular-dynamics trajectory',withheld=['No simulation execution.'])

# Revisit earlier labels under the narrower operation vocabulary and explicit targets.
for r in rows:
    r['annotation_version']=v['version']
    for a in r['labels']:
        if a['facet']=='operation' and a['target']=='document analysis; see rationale':
            a['target']=a['rationale']
    if r['id']=='G02':
        r.setdefault('review_notes',[])
        note='Retained simulation as an external FBA exercise under the narrower definition; network specification alone would be model-construction.'
        if note not in r['review_notes']:r['review_notes'].append(note)
    if r['id']=='A04':
        r['withheld_labels']=['Generic segmentation does not establish a cellular process or disease question; Bioimage analysis is retained.']
for facet in ['scientific_field','modality','operation']:
    used={a['term'] for r in rows for a in r['labels'] if a['facet']==facet}
    for key,t in v[facet].items():t['pilot_status']='exercised_in_sample' if key in used else 'proposed_not_tested'
assert len(rows)==35
assert all(t['pilot_status']=='exercised_in_sample' for t in v['scientific_field'].values())
for name,obj in [('annotations.json',rows),('vocabulary.json',v)]: (ROOT/name).write_text(json.dumps(obj,indent=2)+'\n')
print('Refined',len(rows),'documents; all',len(v['scientific_field']),'candidate fields exercised.')
