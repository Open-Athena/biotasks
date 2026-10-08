"""Auditable lexical proposals, not automatic biological adjudication.

Narrative rules propose topics; code signatures propose operations. Every match
retains source evidence and remains explicitly rule-assigned until reviewed.
"""
FIELD={
'genomics-genetics':r'genom(?:e[- ]wide|ic variation)|genetic varia|genotyp|GWAS|variant call|genome assembly|genome annotation|DNA sequenc|copy.number varia|genetic association',
'transcriptomics':r'RNA[- ]seq|transcriptom|gene expression|differential expression|RNA abundance|alternative splicing',
'epigenomics':r'epigenom|chromatin|DNA methylation|ChIP[- ]seq|ATAC[- ]seq|histone modif|histone mark',
'proteomics':r'proteomic|peptide quantif|protein abundance|protein quantif|mass spectrometry.based protein',
'structural-biology':r'protein structur|molecular structur|molecular dynamics|RNA structur|structural align|protein folding|residue contacts|molecular conform',
'metabolomics':r'metabolomi|metabolite profil|metabolite quantif',
'systems-biology':r'systems biology|metabolic network|flux balance|biochemical network|reaction network|gene regulatory network',
'microbiome':r'microbiom|metagenom|microbial communit|microbiota',
'evolution':r'phylogen|population genetic|coalescent|evolutionary|natural selection|ancestral recombination',
'ecology':r'ecolog|species richness|vegetation|species distribution|environmental gradient',
'immunology':r'immune repertoire|immune receptor|T.cell receptor|B.cell receptor|immunolog|immunophenotyp|TCR repertoir|BCR repertoir',
'neuroscience':r'neuroscien|electrophysiolog|neural activit|brain activit|spike sort|electroencephal|magnetoencephal|neuronal|functional connectiv',
'bioimage-analysis':r'bioimag|microscopy|cell segmentation|nuclei segmentation|histopatholog|fluorescen.*imag|medical imag|radiomic|tissue imag',
'cell-development':r'cell differentiat|cellular differentiat|developmental trajector|cell.fate|embryo develop|cell.cell communic|ligand.receptor interaction',
'biochemistry':r'enzyme kinetic|reaction kinetic|allosteric|binding affinit|biochemical reaction',
'pharmacology':r'drug discover|drug repurpos|drug.target|drug response|toxicolog|pharmacolog|virtual screening|molecular docking|compound activit',
'epidemiology':r'epidemiolog|disease transmission|SIR model|SEIR model|infection dynamic',
'physiology':r'physiolog|musculoskeletal|biomechanic|inverse kinematics|inverse dynamics',
}
MODALITY={
'airr':r'T.cell receptor|B.cell receptor|TCR sequenc|BCR sequenc|immune receptor sequenc|VDJ|V\(D\)J',
'methylation-array':r'methylation array|450K|EPIC array|Infinium',
'rgb-image':r'RGB imag|color imag|colour imag|airborne imag',
'scrna':r'single.cell RNA|scRNA|single.cell transcriptom',
'bulk-rna':r'bulk RNA|bulk transcriptom|bulk gene.expression',
'dna-variants':r'genotyp|single.nucleotide polymorph|\bSNPs?\b|\bVCF\b|genetic variants',
'metabolite-profile':r'metabolite profil|metabolite abundance|metabolomics data',
'growth':r'growth rate|growth curve|optical density',
'structure':r'atomic coordinates|molecular coordinates|PDB file|protein structur|RNA structur',
 'trajectory':r'molecular dynamics trajector|MD trajector|simulation trajector|DCD file',
'flow-cytometry':r'flow cytometr|FCS files',
'mass-cytometry':r'mass cytometr|CyTOF',
'microscopy':r'microscopy|microscopic imag',
'community-profile':r'OTU table|ASV table|microbial abundance|taxonomic abundance|microbiome data',
'electrophysiology':r'electrophysiolog|\bEEG\b|\bMEG\b|local field potential|extracellular recording',
'atac':r'ATAC[- ]seq|chromatin accessib',
'chip':r'ChIP[- ]seq|chromatin immunoprecipitation',
'mass-spectrometry':r'mass spectrom|\bmzML\b|\bmzXML\b',
'spatial-expression':r'spatial transcriptom|spatial gene.expression|Slide.seq|Visium',
'sequences':r'amino.acid sequence|nucleotide sequence|protein sequence|DNA sequence|RNA sequence|FASTA',
'ancestral-trees':r'tree sequence|ancestral tree|genealog',
'model-data':r'reaction network|model parameters|initial conditions|SBML',
'motion-force':r'motion capture|ground reaction force|marker trajectories',
'chemical-assay':r'SMILES|compound activity|bioassay|chemical structures',
'community-vegetation':r'vegetation data|species abundance|community matrix|community data',
'protein-profile':r'protein abundance|protein expression|protein quantif',
}
# Specific source calls; generic fit()/predict()/plot() do not establish domain work.
OP={
'data-access':r'\b(?:read_h5ad|read_csv|readRDS|read\.table|read\.csv|readFCS|read\.FCS|getGEO)\s*\(',
'phenotyping':r'pcv\.analyze\.(?:size|color|bound_horizontal)\s*\(',
'data-preparation':r'\b(?:read10xCounts|Read10X|DESeqDataSetFromMatrix|AnnData|SummarizedExperiment|prepData)\s*\(',
'qc':r'\b(?:calculate_qc_metrics|filter_cells|filter_genes|addPerCellQC|perCellQCMetrics|filterByExpr)\s*\(',
'normalization':r'\b(?:normalize_total|normalize_per_cell|logNormCounts|NormalizeData|calcNormFactors|estimateSizeFactors|preprocessQuantile|rlog|vst)\s*\(',
'feature-selection':r'\b(?:highly_variable_genes|FindVariableFeatures|modelGeneVar|getTopHVGs)\s*\(',
'dimension-reduction':r'\b(?:PCA|UMAP|TSNE|prcomp|RunPCA|RunUMAP|RunTSNE|runPCA|runUMAP|runTSNE)\s*\(|\.(?:pca|umap|tsne)\s*\(',
'clustering':r'\b(?:kmeans|KMeans|DBSCAN|leiden|louvain|FindClusters|clusterRows|define_clonotype_clusters)\s*\(',
'marker-testing':r'\b(?:rank_genes_groups|FindAllMarkers|findMarkers|scoreMarkers)\s*\(',
'association':r'\b(?:runSingleTraitGwas|linear_regression_rows|logistic_regression_rows)\s*\(',
'group-comparison':r'\b(?:DESeq|glmQLFTest|glmLRT|exactTest|eBayes|differential_accessibility|associationTest|startVsEndTest|ttest_ind|wilcox\.test)\s*\(',
'annotation':r'\b(?:SingleR|annotatePeak|predictCoding|classifyify)\s*\(',
'structural-comparison':r'\b(?:RMSD|AlignTraj|alignto|superimpose|rmsd)\s*\(',
'geometry':r'\b(?:Contacts|distance_array|calc_dihedrals|calc_angles|radius_of_gyration)\s*\(',
'segmentation':r'\b(?:watershed|Cellpose|CellposeModel|bwlabel|compute_masks)\s*\(',
'diversity':r'\b(?:estimate_richness|alpha_diversity|beta_diversity|diversity|specnumber|rarefy)\s*\(',
'descriptive-analysis':r'\b(?:ggplot|FeaturePlot|DimPlot|pheatmap)\s*\(|\b(?:plt|sns)\.(?:plot|scatter|hist|heatmap)\s*\(',
'simulation':r'\b(?:sim_ancestry|sim_mutations|solve_ivp|run_time_course|simulate_model|odeint)\s*\(',
'prediction':r'\b(?:RandomForestClassifier|RandomForestRegressor|LogisticRegression|SVC|XGBClassifier|train_test_split|cross_val_score)\s*\(',
'integration':r'\b(?:IntegrateData|IntegrateLayers|RunHarmony|run_harmony|harmony_integrate|mnn_correct|fastMNN|bbknn)\s*\(',
'alignment':r'\b(?:pairwiseAlignment|align_optimal|pairwise_align)\s*\(',
'quantification':r'\b(?:windowCounts|featureCounts|summarizeOverlaps|quantify)\s*\(',
'enrichment':r'\b(?:gsva|fgsea|enrichGO|enrichKEGG|gseGO|run_gsea|prerank)\s*\(',
'model-construction':r'\b(?:add_reaction|add_species|set_reaction_parameters|Reaction)\s*\(',
'inverse-modeling':r'\b(?:InverseKinematicsTool|InverseDynamicsTool)\s*\(',
'statistical-modeling':r'\b(?:fitGAM|glmQLFit|glmFit|lmFit|glm|gam|lmer)\s*\(',
'spatial-statistics':r'\b(?:spatial_autocorr|nhood_enrichment|co_occurrence|ripley|spatial_neighbors)\s*\(',
}

# v0.4 expansion: clinical records and representations exposed missing concepts.
FIELD['clinical-informatics']=r'clinical data|clinical records|patient outcomes|electronic health records|survival analysis'
MODALITY['medical-imaging']=r'\bMRI\b|magnetic resonance imag|computed tomography|\bCT images|radiomic'
MODALITY['clinical-records']=r'clinical data|clinical records|patient outcomes|survival data|electronic health records'
OP['feature-extraction']=r'\bRadiomicsFeatureExtractor\s*\(|\bextractor\.execute\s*\(|\bmodel\s*\(\s*input_ids'
