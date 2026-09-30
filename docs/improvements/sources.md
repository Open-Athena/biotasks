# Selected sources

[Catalog](README.md) · [Research method](research-method.md)

This register records inclusion rationale and the catalog mapping for 41 selected
publications and four upstream software fixes. Source IDs are local citation keys,
not quality scores. Locations
supporting individual claims appear in the entries. Access codes record what was
inspected on 2026-09-30: **T**, relevant article/PDF text; **E**, indexed section
excerpts or captions, sometimes after a publisher/PMC access failure; **C**,
pinned source changes and regression-test text. None means every supplement or
dataset was reviewed. These are primary publications, author/institutional copies,
original guidance papers and software-maintainer records. See the method for
discovery sources not treated as evidence of defects.

## Biological and statistical sources

### B01

Ziemann, Eren and El-Osta (2016).
[Gene name errors are widespread in the scientific literature](https://pmc.ncbi.nlm.nih.gov/articles/PMC4994289/).
DOI: 10.1186/s13059-016-1044-7.

Included for observed spreadsheet corruption; [I01](README.md#i01). Access: E.

### B02

Abeysooriya et al. (2021).
[Gene name errors: Lessons not learned](https://pmc.ncbi.nlm.nih.gov/articles/PMC8357140/).
DOI: 10.1371/journal.pcbi.1008984.

Included for a later audit of the same mechanism; [I01](README.md#i01).
Detection/corpus differences prevent a simple prevalence trend. Access: E.

### B03

Oh et al. (2022, version 2; originally 2020).
[HGNChelper: identification and correction of invalid gene symbols for human and mouse](https://pmc.ncbi.nlm.nih.gov/articles/PMC7856679/).
DOI: 10.12688/f1000research.28033.2.

Included for resource audits and contextual symbol reconciliation;
[I02](README.md#i02). Access: E.

### B04

Leek et al. (2010).
[Tackling the widespread and critical impact of batch effects in high-throughput data](https://pmc.ncbi.nlm.nih.gov/articles/PMC3880143/).
DOI: 10.1038/nrg2825.

Included for empirical batch structure and identifiability limits;
[I03](README.md#i03). Access: E.

### B05

Squair et al. (2021).
[Confronting false discoveries in single-cell differential expression](https://pmc.ncbi.nlm.nih.gov/articles/PMC8479118/).
DOI: 10.1038/s41467-021-25960-2.

Included for controlled evidence about biological replication;
[I04](README.md#i04). Access: E.

### B06

Price et al. (2006).
[Principal components analysis corrects for stratification in genome-wide association studies](https://biostat.jhsph.edu/~iruczins/teaching/misc/2008.140.668/papers/price2006.pdf).
DOI: 10.1038/ng1847.

Included for ancestry-confounding mechanisms and adjustment;
[I05](README.md#i05). Access: T, institutional PDF after publisher access failed.

### B07

Smialowski, Frishman and Kramer (2010; online 2009).
[Pitfalls of supervised feature selection](https://pmc.ncbi.nlm.nih.gov/articles/PMC2815655/).
DOI: 10.1093/bioinformatics/btp621.

Included for controlled feature-selection leakage examples;
[I06](README.md#i06). Access: E.

### B08

Whalen et al. (2022; online 2021).
[Navigating the pitfalls of applying machine learning in genomics](https://escholarship.org/content/qt6f5210xq/qt6f5210xq.pdf).
DOI: 10.1038/s41576-021-00434-9.

Issue seed; [I07](README.md#i07), [I08](README.md#i08). Access: T,
institutional manuscript after publisher access failed.

### B09

Saito and Rehmsmeier (2015).
[The Precision-Recall Plot Is More Informative than the ROC Plot When Evaluating Binary Classifiers on Imbalanced Datasets](https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0118432).
DOI: 10.1371/journal.pone.0118432.

Included for metric interpretation under imbalance; [I09](README.md#i09).
Access: T.

### B10

Williams et al. (2014).
[RNA-seq Data: Challenges in and Recommendations for Experimental Design and Analysis](https://pmc.ncbi.nlm.nih.gov/articles/PMC4230301/).
DOI: 10.1002/0471142905.hg1113s83.

Issue seed; normalization context for [I10](README.md#i10). Access: T/E,
PMC manuscript and indexed sections.

### B11

Robinson and Oshlack (2010).
[A scaling normalization method for differential expression analysis of RNA-seq data](https://pmc.ncbi.nlm.nih.gov/articles/PMC2864565/).
DOI: 10.1186/gb-2010-11-3-r25.

Included for composition effects and a conditional correction;
[I10](README.md#i10). Access: E.

### B12

Young et al. (2010).
[Gene ontology analysis for RNA-seq: accounting for selection bias](https://pmc.ncbi.nlm.nih.gov/articles/PMC2872874/).
DOI: 10.1186/gb-2010-11-2-r14.

Included for nonuniform gene selection in enrichment;
[I11](README.md#i11). Access: E.

### B13

Young and Behjati (2020).
[SoupX removes ambient RNA contamination from droplet-based single-cell RNA sequencing data](https://pmc.ncbi.nlm.nih.gov/articles/PMC7763177/).
DOI: 10.1093/gigascience/giaa151.

Included for experimental controls and tissue applications;
[I12](README.md#i12). Access: E.

### B14

Wolock, Lopez and Klein (2019).
[Scrublet: Computational Identification of Cell Doublets in Single-Cell Transcriptomic Data](https://pmc.ncbi.nlm.nih.gov/articles/PMC6625319/).
DOI: 10.1016/j.cels.2018.11.005.

Included for multiplet mechanisms and experimental validation;
[I13](README.md#i13). Access: E.

### B15

Luecken and Theis (2019).
[Current best practices in single-cell RNA-seq analysis: a tutorial](https://link.springer.com/article/10.15252/msb.20188746).
DOI: 10.15252/msb.20188746.

Issue seed; contextual QC guidance for [I14](README.md#i14). Access: T.

### B16

Luecken et al. (2022; online 2021).
[Benchmarking atlas-level data integration in single-cell genomics](https://pmc.ncbi.nlm.nih.gov/articles/PMC8748196/).
DOI: 10.1038/s41592-021-01336-8.

Included for biological-conservation versus batch-removal tradeoffs;
[I15](README.md#i15). Access: E, published study rather than earlier preprint counts.

### B17

Andrews and Hemberg (2019, version 2; originally 2018).
[False signals induced by single-cell imputation](https://pmc.ncbi.nlm.nih.gov/articles/PMC6415334/).
DOI: 10.12688/f1000research.16613.2.

Included for null/simulation evidence about downstream inference;
[I16](README.md#i16). Access: E.

### B18

Tirosh (2026).
[Pitfalls in analysis and interpretation of single-cell RNA-seq data in cancer](https://academic.oup.com/noa/article/8/Supplement_1/i57/8499781).
DOI: 10.1093/noajnl/vdaf047.

Issue seed; [I17](README.md#i17), [I18](README.md#i18). Access: T.

### B19

Salter et al. (2014).
[Reagent and laboratory contamination can critically impact sequence-based microbiome analyses](https://link.springer.com/article/10.1186/s12915-014-0087-z).
DOI: 10.1186/s12915-014-0087-z.

Included for controls exposing low-biomass contamination;
[I19](README.md#i19). Access: T.

### B20

Friedman and Alm (2012).
[Inferring Correlation Networks from Genomic Survey Data](https://pmc.ncbi.nlm.nih.gov/articles/PMC3447976/).
DOI: 10.1371/journal.pcbi.1002687.

Included for compositional association mechanisms;
[I20](README.md#i20). Access: E.

### B21

Nearing et al. (2022).
[Microbiome differential abundance methods produce different results across 38 datasets](https://www.nature.com/articles/s41467-022-28034-z).
DOI: 10.1038/s41467-022-28034-z.

Included for null calibration and method sensitivity;
[I21](README.md#i21). Access: T. The null experiment is a subset of the study.

### B22

van de Geijn et al. (2015).
[WASP: allele-specific software for robust molecular quantitative trait locus discovery](https://pmc.ncbi.nlm.nih.gov/articles/PMC4626402/).
DOI: 10.1038/nmeth.3582.

Included for allele-dependent mapping and mitigation;
[I22](README.md#i22). Access: E.

### B23

Krusche et al. (2019).
[Best practices for benchmarking germline small-variant calls in human genomes](https://pmc.ncbi.nlm.nih.gov/articles/PMC6699627/).
DOI: 10.1038/s41587-019-0054-x.

Included for representation and coverage limitations;
[I23](README.md#i23), [I24](README.md#i24). Access: T.

### B24

Salzberg et al. (2012).
[GAGE: A critical evaluation of genome assemblies and assembly algorithms](https://pmc.ncbi.nlm.nih.gov/articles/PMC3290791/).
DOI: 10.1101/gr.131383.111.

Included for accuracy/contiguity comparisons; [I25](README.md#i25). Access: E.

### B25

Szánthó et al. (2023).
[Compositionally Constrained Sites Drive Long-Branch Attraction](https://pmc.ncbi.nlm.nih.gov/articles/PMC10405358/).
DOI: 10.1093/sysbio/syad013.

Included for known-tree simulations and empirical sensitivity;
[I26](README.md#i26). Access: E.

### B26

Degnan and Rosenberg (2006).
[Discordance of Species Trees with Their Most Likely Gene Trees](https://journals.plos.org/plosgenetics/article?id=10.1371/journal.pgen.0020068).
DOI: 10.1371/journal.pgen.0020068.

Included for a theoretical counterexample to majority genealogy;
[I27](README.md#i27). Access: T.

### B27

Zhang et al. (2015).
[ProteinInferencer: Confident protein identification and multiple experiment comparison for large scale proteomics projects](https://pmc.ncbi.nlm.nih.gov/articles/PMC4630118/).
DOI: 10.1016/j.jprot.2015.07.006.

Included for inference-level FDR distinctions;
[I28](README.md#i28). Access: E.

### B28

Deutsch et al. (2016).
[Human Proteome Project Mass Spectrometry Data Interpretation Guidelines 2.1](https://pmc.ncbi.nlm.nih.gov/articles/PMC5096969/).
DOI: 10.1021/acs.jproteome.6b00392.

Included for individual-hit interpretation; [I29](README.md#i29). Access: E.

### B29

Alseekh et al. (2021).
[Mass spectrometry-based metabolomics: a guide for annotation, quantification and best reporting practices](https://pmc.ncbi.nlm.nih.gov/articles/PMC8592384/).
DOI: 10.1038/s41592-021-01197-1.

Included for identity ambiguity and confidence reporting;
[I30](README.md#i30). Access: E.

### B30

Reinke et al. (2024).
[Understanding metric-related pitfalls in image analysis validation](https://pmc.ncbi.nlm.nih.gov/articles/PMC11181963/).
DOI: 10.1038/s41592-023-02150-0.

Included for concrete metric/target mismatches;
[I31](README.md#i31). Access: E, including Fig. 1 caption.

### B31

Tiwari et al. (2021).
[Reproducibility in systems biology modelling](https://pmc.ncbi.nlm.nih.gov/articles/PMC7901289/).
DOI: 10.15252/msb.20209982.

Included for an audit with an explicit reproduction criterion;
[I32](README.md#i32). Access: E.

### B32

Varma and Simon (2006).
[Bias in error estimation when using cross-validation for model selection](https://link.springer.com/article/10.1186/1471-2105-7-91).
DOI: 10.1186/1471-2105-7-91.

Included for tuning-selection bias and nested evaluation;
[I33](README.md#i33). Access: T.

### B33

Benjamini and Hochberg (1995).
[Controlling the False Discovery Rate: a Practical and Powerful Approach to Multiple Testing](https://www.math.tau.ac.il/~yekutiel/eBayes/bh_1995.pdf).
DOI: 10.1111/j.2517-6161.1995.tb02031.x.

Included for the original error criterion and independence theorem;
[I34](README.md#i34). Access: T, institutional PDF.

### B34

Wasserstein and Lazar (2016).
[The ASA's Statement on p-Values: Context, Process, and Purpose](https://www.stat.berkeley.edu/~aldous/Real_World/ASA_statement.pdf).
DOI: 10.1080/00031305.2016.1154108.

Included for significance/importance distinctions and reporting guidance;
[I35](README.md#i35). Access: T, institutional PDF.

## Software and scientific-computing sources

### S01

Shen et al. (2026).
[SERA: Soft-Verified Efficient Repository Agents, version 3](https://arxiv.org/html/2601.20789v3#S3.SS1).
arXiv:2601.20789v3, 29 May 2026.

Discovery source, not evidence that every suggested change is beneficial.
Inspected §3.1 and the linked
[prompt-generation script](https://github.com/allenai/SERA/blob/1ca8673bd527b164dc9eb89841c96416ec8ce1a7/sera/datagen/data/create_rollout_one_prompts.py)
at commit `1ca8673bd527b164dc9eb89841c96416ec8ce1a7`. The script contains 30
seed directions and code to generate additional prompts; it was not executed.
Its directions are not an empirically labeled distribution of defects. Access: T.

### S02

Just, Jalali and Ernst (2014).
[Defects4J: A Database of Existing Faults to Enable Controlled Testing Studies for Java Programs](https://homes.cs.washington.edu/~mernst/pubs/bug-database-issta2014.pdf).
DOI: 10.1145/2610384.2628055.

Followed from SERA; real-defect evidence pattern for [I45](README.md#i45).
The original collection is selected for reproducible, isolated source fixes,
excluding configuration/documentation fixes. It is not a representative survey
of all software failures. Access: T, author PDF, §2–3.

### S03

Widyasari et al. (2020).
[BugsInPy: A database of existing bugs in Python programs to enable controlled testing and debugging studies](https://arxiv.org/pdf/2401.15481v1).
DOI: 10.1145/3368089.3417943.

Followed from SERA; Python counterpart for [I45](README.md#i45). Access: T,
§2–3 via the 2024 arXiv deposit of the 2020 paper, recovered after earlier PDF
failures. Selection requires isolated source fixes with exposing tests;
configuration/documentation fixes are excluded. Original 493-bug scope is
distinct from the later snapshot studied in S07.

### S04

Wilson et al. (2014).
[Best Practices for Scientific Computing](https://journals.plos.org/plosbiology/article?id=10.1371/journal.pbio.1001745).

Guidance for [I36](README.md#i36), [I37](README.md#i37),
[I38](README.md#i38). Access: T, Box 1.

### S05

Wilson et al. (2017).
[Good enough practices in scientific computing](https://journals.plos.org/ploscompbiol/article?id=10.1371/journal.pcbi.1005510).
DOI: 10.1371/journal.pcbi.1005510.

Included for usable scientific artifacts and bounded small-project guidance;
[I39](README.md#i39). Access: T, software section and Box 3.

### S06

Sandve et al. (2013).
[Ten Simple Rules for Reproducible Computational Research](https://journals.plos.org/ploscompbiol/article?id=10.1371/journal.pcbi.1003285).
DOI: 10.1371/journal.pcbi.1003285.

Included for workflow provenance and randomness;
[I40](README.md#i40), [I41](README.md#i41). Access: T.

### S07

Aguilar, Grayson and Marinov (2023).
[Reproducing and Improving the BugsInPy Dataset](https://mir.cs.illinois.edu/~marinov/publications/AguilarETAL23ReproducingBugsInPy.pdf).
SCAM 2023.

Empirical follow-up; [I42](README.md#i42), [I43](README.md#i43),
[I44](README.md#i44). Access: T, §II–III.

## Software-maintainer records

These records were discovered through BugsInPy at commit
`11c5f1eea954a42132cfd06bf257766a7963e0fd`. Metadata, patches and named tests
were cross-checked against upstream commits. They establish documented examples,
not recurrence rates; tests were inspected but not executed here.

### S08

pandas maintainers (2020).
[Categorical dtype classification fix](https://github.com/pandas-dev/pandas/commit/e41ee47a90bb1d8a1fa28fcefcd45ed8ef5cb946).
[BugsInPy pandas/1](https://github.com/soarsmu/BugsInPy/tree/11c5f1eea954a42132cfd06bf257766a7963e0fd/projects/pandas/bugs/1).

Included for logical-type dispatch; [I46](README.md#i46). Access: C,
`pandas/core/dtypes/common.py` and `pandas/tests/dtypes/test_dtypes.py`.

### S09

pandas maintainers (2020).
[Compound-label scalar indexing fix](https://github.com/pandas-dev/pandas/commit/55e8891f6d33be14e0db73ac06513129503f995c).
[BugsInPy pandas/2](https://github.com/soarsmu/BugsInPy/tree/11c5f1eea954a42132cfd06bf257766a7963e0fd/projects/pandas/bugs/2).

Included for indexing semantics; [I47](README.md#i47). Access: C,
`pandas/core/indexing.py` and `pandas/tests/indexing/test_scalar.py`.

### S10

pandas maintainers (2020).
[Explicit errors for unsupported time-index conversions](https://github.com/pandas-dev/pandas/commit/d3a6a3a58e1a6eb68b8b8399ff252b8f4501950e).
[BugsInPy pandas/3](https://github.com/soarsmu/BugsInPy/tree/11c5f1eea954a42132cfd06bf257766a7963e0fd/projects/pandas/bugs/3).

Included as a concrete contract-checking repair; [I36](README.md#i36). Access: C,
`pandas/core/series.py`, `test_to_period_raises` and `test_to_timestamp_raises`.

### S11

pandas maintainers (2020).
[Optional-indexer return fix](https://github.com/pandas-dev/pandas/commit/2250ddfaff92abaff20a5bcd78315f5d4bd44981).
[BugsInPy pandas/4](https://github.com/soarsmu/BugsInPy/tree/11c5f1eea954a42132cfd06bf257766a7963e0fd/projects/pandas/bugs/4).

Included for branch-specific API consistency; [I48](README.md#i48). Access: C,
`pandas/core/indexes/base.py` and `pandas/tests/indexes/multi/test_join.py`.
