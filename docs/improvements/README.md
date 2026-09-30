# Improvements to computational biology artifacts

[Documentation overview](../README.md) · [Selected sources](sources.md) ·
[Research method and consolidation](research-method.md)

This catalog addresses [issue #7](https://github.com/Open-Athena/biotasks/issues/7)
with 48 improvement opportunities drawn from software engineering, statistics/ML,
and computational biology. It includes repairs, preventive checks, changes to
otherwise valid code, and better reporting of irreparable limitations. The
source register contains 41 publications and four upstream software fixes,
including the SERA discovery source and its linked implementation. Literature
and source changes were inspected on 2026-09-30; the cited analyses and tests
were not rerun.

The organizing unit is a starting condition, a possible change, and a benefit
under stated conditions. These are research findings, not a checklist that every
artifact must satisfy. No entry establishes suitability for synthetic tasks, and
this work does not implement or evaluate tasks.

## Reading the catalog

**Scope** identifies the knowledge area and biological relevance. **Documented**
means the source discusses the named biological application; it does not mean
the recommended change was experimentally validated there. **Inferred** means
this synthesis proposes a transfer from general evidence to biological software.
An entry may combine knowledge areas. Group headings are navigation, not a fixed
ontology or a ranking.

**Opportunity** describes the starting artifact, change and intended benefit:
correctness, scientific validity, robustness, reproducibility, efficiency or
maintainability. Benefits are conditional; a recommendation is not proof of a
defect or a measured improvement. Diagnostic and reporting changes can be useful
when the underlying experiment cannot be repaired computationally.

**Evidence and conditions** distinguishes observed defects, demonstrated
mechanisms, conditional risks, intrinsic limitations and recommendations. It also
identifies evidence from audits, controlled comparisons, modified observed data,
simulations, theory or guidance. Demonstrating a mechanism does not establish its
prevalence. Historical benchmarks do not rank current software releases.

## Index

| Workflow area | Opportunities |
| --- | --- |
| Identifiers and study design | [I01](#i01) preserve identifiers; [I02](#i02) reconcile nomenclature; [I03](#i03) diagnose batch confounding; [I04](#i04) respect biological replication; [I05](#i05) account for ancestry |
| Prediction and evaluation | [I06](#i06) fit feature selection within training; [I07](#i07) split by prediction unit; [I08](#i08) validate transfer; [I09](#i09) assess rare-positive precision; [I33](#i33) separate tuning and evaluation |
| Expression and enrichment | [I10](#i10) assess composition; [I11](#i11) account for gene-selection bias |
| Single-cell analysis | [I12](#i12) assess ambient RNA; [I13](#i13) assess multiplets; [I14](#i14) contextualize QC; [I15](#i15) preserve relevant biology; [I16](#i16) validate inference after imputation; [I17](#i17) qualify trajectories; [I18](#i18) assess CNA references |
| Microbiome and networks | [I19](#i19) assess contamination; [I20](#i20) respect compositional data; [I21](#i21) assess abundance-test calibration |
| Sequence analysis | [I22](#i22) assess allele mapping; [I23](#i23) compare variant haplotypes; [I24](#i24) state benchmark territory; [I25](#i25) assess assembly accuracy |
| Phylogenetics | [I26](#i26) assess evolutionary models; [I27](#i27) distinguish gene and species histories |
| Proteomics and metabolomics | [I28](#i28) match FDR to inference level; [I29](#i29) qualify individual hits; [I30](#i30) distinguish annotation from identification |
| Imaging and mechanistic models | [I31](#i31) match metrics to biological targets; [I32](#i32) complete model specifications |
| General inference | [I34](#i34) account for multiplicity; [I35](#i35) report effect and uncertainty |
| Scientific software and workflows | [I36](#i36) check contracts; [I37](#i37) consolidate repeated logic; [I38](#i38) profile bottlenecks; [I39](#i39) document an executable example; [I40](#i40) preserve workflow provenance; [I41](#i41) record randomness; [I42](#i42) specify environments; [I43](#i43) reuse compatible environments; [I44](#i44) preserve argument grouping; [I45](#i45) retain defect regressions |
| Data-processing software | [I46](#i46) distinguish logical types; [I47](#i47) preserve compound labels; [I48](#i48) honor optional-return contracts |

## Identifiers and study design

### I01

**Preserve identifier strings during import and export.**

**Scope:** software/data handling and biology; documented gene-list spreadsheets.

**Opportunity — correctness:** when spreadsheet type inference converts gene
symbols to dates or numbers, import identifiers as text and check round trips
against the original. Recover corrupted values from authoritative inputs rather
than guessing inverse conversions.

**Evidence and conditions:** observed defects in publication audits,
[B01](sources.md#b01), main audit and supplementary-file description, and
[B02](sources.md#b02), Results on error types. Their denominators concern papers
with relevant spreadsheets, not all biological research. Neither audit tests
every current spreadsheet configuration.

### I02

**Reconcile changing nomenclature before joining tables.**

**Scope:** biology and data handling; documented human/mouse annotation resources.

**Opportunity — correctness:** when old symbols fail to match current tables,
resolve aliases against an organism- and version-specific authority, preserve
original identifiers, and expose ambiguous mappings rather than forcing a join.

**Evidence and conditions:** resource audit and correction method,
[B03](sources.md#b03), GEO and MSigDB applications. Invalid current symbols do
not establish invalid original measurements. This is nomenclature reconciliation,
distinct from the file corruption in [I01](#i01).

### I03

**Diagnose confounding before adjusting batch effects.**

**Scope:** biology and statistics; documented high-throughput molecular studies.

**Opportunity — scientific validity:** when condition covaries with processing
batch, inspect metadata and estimability, model identifiable nuisance effects,
and report unresolved confounding. This can prevent a technical contrast from
being presented as a biological effect.

**Evidence and conditions:** conditional risk supported by public-data analyses
and statistical guidance, [B04](sources.md#b04), Table 1 and statistical-solutions
discussion. Perfect confounding cannot be resolved computationally from those
data. Distributional normalization is not proof of correction; adjustment can
also remove the target signal ([I15](#i15)).

### I04

**Match inference to biological replication.**

**Scope:** statistics and biology; documented between-donor single-cell comparisons.

**Opportunity — scientific validity:** when cells from one donor are treated as
independent treatment replicates, use a donor-aware analysis, such as an
appropriate aggregated or hierarchical model. Preserve the experimental unit
in the design and reported uncertainty.

**Evidence and conditions:** demonstrated mechanism in simulations and null
comparisons of observed data, [B05](sources.md#b05), Fig. 4. More cells cannot
replace missing biological replicates. The appropriate model depends on the
estimand and design; aggregation is not a universal requirement for every
single-cell question.

### I05

**Account for ancestry structure in association analyses.**

**Scope:** biology and statistics; documented genetic association studies.

**Opportunity — scientific validity:** when ancestry relates to both allele
frequencies and phenotype, assess population structure and use a justified
adjustment in the association model.

**Evidence and conditions:** demonstrated mechanism in simulated disease studies,
with observed genotype analyses, [B06](sources.md#b06), Results and Table 1.
Principal components are one approach; a fixed component count does not guarantee
adequate correction. Biological ancestry and processing batch ([I03](#i03))
require different covariates even though both can confound inference.

## Prediction and evaluation

### I06

**Fit supervised feature selection inside each training partition.**

**Scope:** statistics/ML; documented biological sequence classification.

**Opportunity — scientific validity:** when outcome-associated features are
selected using the full dataset, move selection into the training procedure and
apply the learned selection to held-out examples. This removes direct use of
evaluation labels in feature choice.

**Evidence and conditions:** demonstrated optimistic estimates in random-data
and randomized-label experiments, [B07](sources.md#b07), Figs. 1–2. This claim
concerns supervised selection; it does not make every fixed, label-independent
transformation invalid. Tuning the complete procedure needs a further separation
([I33](#i33)).

### I07

**Split data according to the intended prediction unit.**

**Scope:** statistics/ML and biology; documented genomic prediction examples.

**Opportunity — scientific validity:** when a claim concerns unseen biological
groups but random row splits share related entities, use partitions reflecting
that target and report their construction.

**Evidence and conditions:** conditional risk, [B08](sources.md#b08), pitfall 2
and Fig. 2. Within-group prediction can be a valid different target. Group-aware
splitting changes the question and may reduce available evaluation data.

### I08

**Qualify or test transfer to a new biological setting.**

**Scope:** statistics/ML and biology; documented genomic prediction guidance.

**Opportunity — scientific validity:** when within-cohort performance is used
to support another population or assay, add relevant external evaluation or
explicitly restrict the claim.

**Evidence and conditions:** intrinsic limitation, [B08](sources.md#b08),
pitfall 1. Independent samples can still be unrepresentative of deployment.
Distribution shift motivates investigation; it does not prove model failure.

### I09

**Evaluate precision for rare-positive discovery.**

**Scope:** statistics/ML; documented classifier evaluations including biological data.

**Opportunity — scientific validity:** when a favorable ROC summary is taken as
evidence that predicted positives are reliable, also report precision–recall
behavior at relevant prevalence and operating points.

**Evidence and conditions:** metric limitation demonstrated with examples and
evaluations, [B09](sources.md#b09), Results comparing ROC and precision–recall.
ROC remains meaningful for its own target. Precision measured after artificially
balancing classes does not directly describe rare-event deployment; neither
curve selects an operating point without decision costs.

## Expression and enrichment

### I10

**Assess composition before choosing count normalization.**

**Scope:** biology and statistics; documented bulk RNA-seq comparisons.

**Opportunity — scientific validity:** when a subset of transcripts consumes
different fractions of reads, inspect composition and choose scaling consistent
with the intended contrast and reference assumptions, rather than relying on
total depth alone.

**Evidence and conditions:** demonstrated mechanism in observed comparisons and
simulations, [B11](sources.md#b11), normalization assumptions and composition
simulations; contextual guidance in [B10](sources.md#b10), normalization section.
Robust scaling also has assumptions and does not by itself recover absolute RNA
per cell. This concerns expression contrasts, unlike network associations in
[I20](#i20).

### I11

**Account for unequal gene selection in enrichment analysis.**

**Scope:** biology and statistics; documented RNA-seq gene-set analysis.

**Opportunity — scientific validity:** when transcript length or abundance
affects entry into a selected list, define the eligible gene population and
use an enrichment analysis that accounts for relevant selection probabilities.

**Evidence and conditions:** demonstrated mechanism and proposed adjustment,
[B12](sources.md#b12), Background and GOseq method, with observed-data reanalysis.
Changed category rankings do not establish biological truth. The selected source
addresses length/count-dependent selection, not every possible annotation or
background-set error.

## Single-cell analysis

### I12

**Assess ambient RNA before interpreting marker coexpression.**

**Scope:** biology; documented droplet single-cell RNA-seq.

**Opportunity — scientific validity:** when cell-free RNA contributes to a
barcode, estimate contamination using appropriate background evidence and assess
how correction changes annotations or conclusions.

**Evidence and conditions:** demonstrated mechanism using species-mixing controls
and observed tissues, [B13](sources.md#b13), Results and Fig. 4. Correction is
model-dependent; unexpected marker expression alone is insufficient evidence
of contamination. Retain uncertainty when background information is inadequate.
A second captured cell ([I13](#i13)) is a different mechanism.

### I13

**Assess multiplets before naming mixed cell states.**

**Scope:** biology; documented single-cell transcriptome analysis.

**Opportunity — scientific validity:** when multiple cells can share a barcode,
use assay-aware multiplet detection or supporting experimental evidence, and
test whether proposed states persist after justified filtering.

**Evidence and conditions:** demonstrated mechanism with synthetic doublets and
experimentally labeled multiplets, [B14](sources.md#b14), embedded/neotypic
distinction and experimental evaluations. Some doublets resemble singlets and
remain difficult to detect. Mixed expression alone does not prove a doublet;
over-filtering can remove real transitional populations.

### I14

**Choose QC thresholds in biological context.**

**Scope:** biology; documented single-cell QC guidance.

**Opportunity — robustness and scientific validity:** when one mitochondrial,
gene-count or library-size threshold is imposed on heterogeneous populations,
inspect joint distributions and population context, document the rule, and
assess sensitivity of conclusions to filtering.

**Evidence and conditions:** conditional risk and recommendation,
[B15](sources.md#b15), QC discussion and Fig. 2. Biological differences can
resemble damage indicators. The tutorial provides neither a universal cutoff nor
a prevalence estimate; departing from its suggested practice is not automatically
an error.

### I15

**Evaluate integration against the biology to be retained.**

**Scope:** biology and statistics; documented single-cell atlas integration.

**Opportunity — scientific validity:** when batch mixing is the only selection
criterion, also assess conservation of the biological distinctions relevant to
the analysis and compare against unintegrated data.

**Evidence and conditions:** demonstrated tradeoff, treated as a conditional
risk, [B16](sources.md#b16), Results and Discussion evaluating batch removal and
biological conservation. Benchmark annotations are imperfect references. A
representation useful for broad cell identity may obscure finer differences;
neither maximum mixing nor avoiding integration is universally preferable.

### I16

**Check inferential validity after imputation.**

**Scope:** biology and statistics; documented single-cell expression analysis.

**Opportunity — scientific validity:** when smoothed or imputed values enter
association or differential-expression tests, assess calibration for that
pipeline and compare with suitable inference on observed measurements.

**Evidence and conditions:** false signals demonstrated in simulations,
permuted observed data and cross-platform comparisons, [B17](sources.md#b17),
Figs. 1 and 4 and Discussion. Attractive visualizations do not validate
inferential uncertainty. Results concern the evaluated methods/settings, not
every later imputation model; visualization and hypothesis testing have
different requirements.

### I17

**Distinguish expression trajectories from demonstrated lineage.**

**Scope:** biology; documented cancer single-cell interpretation guidance.

**Opportunity — scientific validity:** when an expression ordering is presented
as ancestry or direction of transition, restrict the claim or obtain independent
temporal/lineage evidence.

**Evidence and conditions:** intrinsic limitation, [B18](sources.md#b18),
pitfall 5 and Table 1. A plausible path through expression states alone does not
establish actual lineage history. This is an improvement to interpretation, not
a promise that another trajectory algorithm repairs missing evidence.

### I18

**Assess references used for expression-derived copy number.**

**Scope:** biology; documented cancer single-cell analysis guidance.

**Opportunity — scientific validity:** when CNA inference depends on a normal
reference, assess reference suitability and corroborate consequential calls
where possible.

**Evidence and conditions:** conditional risk, [B18](sources.md#b18), pitfall 3
and Table 1. Expression differences can mimic copy-number differences. Reference
choice and biological context matter; inferred CNA is not equivalent to a DNA
measurement.

## Microbiome and networks

### I19

**Use contamination evidence in low-biomass analyses.**

**Scope:** biology; documented microbiome sequencing.

**Opportunity — scientific validity:** when low biomass makes reagent DNA
influential, incorporate available blanks, biomass and batch information into
contamination assessment, and report sensitivity or unresolved limitations.

**Evidence and conditions:** demonstrated mechanism in dilution controls and
observed samples, [B19](sources.md#b19), serial-dilution Results and
nasopharyngeal example. A taxon's identity or low abundance alone does not prove
contamination. Missing controls cannot be manufactured computationally, and
indiscriminate deletion can remove real organisms.

### I20

**Match association analysis to compositional measurements.**

**Scope:** biology and statistics; documented microbial community networks.

**Opportunity — scientific validity:** when relative abundances are correlated
as if they were absolute measurements, use a justified compositional model or
additional absolute information and qualify the resulting associations.

**Evidence and conditions:** denominator-induced artifacts demonstrated with
simulated networks and community data, [B20](sources.md#b20), Results on
compositional effects. Behavior depends on community structure and model
assumptions. Even a well-estimated association does not establish direct
ecological interaction.

### I21

**Assess calibration of differential-abundance procedures.**

**Scope:** biology and statistics; documented microbiome analyses.

**Opportunity — scientific validity:** when nominal thresholds are assumed to
behave interchangeably across methods, examine relevant calibration evidence
and design-valid null checks, and report sensitivity to method assumptions.

**Evidence and conditions:** demonstrated discoveries under randomized
within-group labels, [B21](sources.md#b21), false-positive analysis; other
comparisons span 38 datasets. Null relabeling requires exchangeability. Method
disagreement on real contrasts does not identify the true taxa, establish a
universal best method, or settle all normalization choices.

## Sequence analysis

### I22

**Assess allele-sensitive read assignment.**

**Scope:** biology; documented allele-specific molecular analyses.

**Opportunity — scientific validity:** when alleles have different mapping
probabilities, apply an appropriate bias-aware mapping/filtering procedure and
evaluate residual bias before interpreting allelic imbalance.

**Evidence and conditions:** demonstrated mechanism in simulated reads and
molecular data analyses, [B22](sources.md#b22), Fig. 1. Personalized or masked
references need not eliminate bias. Filtering sacrifices reads and can change
coverage; greater sequencing depth alone does not remove systematic assignment
preference.

### I23

**Compare represented haplotypes when variant records differ.**

**Scope:** biology and software/data handling; documented small-variant benchmarking.

**Opportunity — correctness:** when literal VCF matching reports discordance
between equivalent variants, use sequence-aware comparison with an explicit
allele/genotype matching contract.

**Evidence and conditions:** demonstrated representation mechanism,
[B23](sources.md#b23), Fig. 2 and accompanying discussion. Left alignment and
trimming do not resolve every complex case. The comparison must retain the
intended genotype and phasing semantics.

### I24

**Report the genomic territory covered by a benchmark.**

**Scope:** biology and statistics; documented germline small-variant evaluation.

**Opportunity — scientific validity:** when confident-region scores are
generalized genome-wide, report the evaluated regions and variant strata and
restrict unsupported claims.

**Evidence and conditions:** benchmark limitation, [B23](sources.md#b23),
PrecisionFDA lessons. A call outside confident territory is not automatically
false. Historical truth sets do not establish current coverage; expanding
evaluation requires trustworthy additional evidence.

### I25

**Assess assembly correctness alongside contiguity.**

**Scope:** biology; documented genome assembly comparisons.

**Opportunity — scientific validity:** when assembly selection relies on N50,
also assess misassemblies, missing sequence and other accuracy/completeness
criteria supported by the available references.

**Evidence and conditions:** demonstrated mismatches between contiguity and
accuracy in observed short-read benchmarks, [B24](sources.md#b24), corrected
contiguity and accuracy analyses, Tables 2–7. N50 remains a valid continuity
statistic. Reference disagreement is not always an assembly error, and the
historical comparison does not rank present-day assemblers.

## Phylogenetics

### I26

**Assess evolutionary model adequacy as well as tree support.**

**Scope:** biology and statistics; documented phylogenomic analyses.

**Opportunity — scientific validity:** when strong support is obtained under
models that poorly represent site-specific composition, investigate adequacy and
sensitivity to justified alternative models.

**Evidence and conditions:** long-branch attraction demonstrated using known-tree
simulations and empirical reanalyses, [B25](sources.md#b25), Figs. 2–3. Support
conditional on a model is not evidence of its adequacy. Empirical preferred trees
are not known simulated truth; model changes do not guarantee the true topology.

### I27

**Model the distinction between gene and species histories.**

**Scope:** biology and statistics; documented theoretical species-tree inference.

**Opportunity — scientific validity:** when the most frequent gene tree is
assumed to be the species tree, consider inference that models relevant
gene-history variation and state its assumptions.

**Evidence and conditions:** mathematical counterexample under a coalescent
model, [B26](sources.md#b26), Results on anomalous gene trees. In particular
branch-length regimes, majority gene-tree voting can fail even with correct
genealogies. This supplies no empirical prevalence estimate or universal
endorsement of an alternative species-tree estimator.

## Proteomics and metabolomics

### I28

**Match error control to the reported inference level.**

**Scope:** biology and statistics; documented proteomics aggregation.

**Opportunity — scientific validity:** when spectrum-match FDR is used to
justify protein identifications, estimate/control errors at the protein level
using a suitable inference procedure.

**Evidence and conditions:** demonstrated accumulation mechanism in large-scale
proteomics, [B27](sources.md#b27), protein-FDR discussion. Correct matches may
repeatedly support existing proteins while erroneous matches add new ones.
Match-level control does not automatically transfer across aggregation. No
fixed peptide count guarantees identity in every setting.

### I29

**Separate list-level error control from individual-hit confidence.**

**Scope:** biology and statistics; documented novel protein identification guidance.

**Opportunity — scientific validity:** when a global FDR cutoff is treated as
proof of a particular unusual identification, qualify the claim and inspect
appropriate independent identification evidence.

**Evidence and conditions:** intrinsic statistical limitation and community
guidance, [B28](sources.md#b28), guideline 8. Passing the threshold does not
establish certainty for each hit. This catalog does not import the HPP's
submission requirements as universal thresholds. Unlike [I28](#i28), the
inference level need not change.

### I30

**Distinguish tentative metabolite annotation from identification.**

**Scope:** biology; documented mass-spectrometry metabolomics guidance.

**Opportunity — scientific validity:** when a database mass match is reported
as a unique molecule, retain an appropriate confidence label and use relevant
orthogonal evidence before making identity-dependent conclusions.

**Evidence and conditions:** measurement limitation based on chemical reasoning,
[B29](sources.md#b29), peak-identification discussion. Isomers, adducts and
fragments can create ambiguity. A tentative annotation is useful when reported
as such; neither one additional measurement nor one instrument resolves every
possible identity.

## Imaging and mechanistic models

### I31

**Validate the biological target of an imaging pipeline.**

**Scope:** biology and statistics; documented biomedical image analysis examples.

**Opportunity — scientific validity:** when pixel agreement is used to justify
object counting or localization, add metrics that assess those intended targets
and inspect their failure modes.

**Evidence and conditions:** metric limitation demonstrated by constructed
examples and expert synthesis, [B30](sources.md#b30), Fig. 1 and category P1.
Good pixel scores can coexist with missed objects. Metrics require appropriate
reference annotations and aggregation; no single metric is invalid or sufficient
for every imaging question.

### I32

**Complete the executable specification of a mechanistic model.**

**Scope:** biology and software; documented systems-biology kinetic models.

**Opportunity — reproducibility and correctness:** when equations, parameters
or initial conditions are missing/inconsistent, reconcile the specification
with authoritative evidence and provide the simulation configuration needed to
reproduce the stated result.

**Evidence and conditions:** observed defects in a curation audit,
[B31](sources.md#b31), assessment protocol and failure-cause analysis. Some
failures remained unexplained; not all can be assigned to missing parameters.
Reconstructing a principal figure in different software was the audit criterion,
not experimental validation of the biological model. Do not invent missing values.

## General inference

### I33

**Separate model tuning from performance estimation.**

**Scope:** statistics/ML; documented motivation in high-dimensional biomedical prediction.

**Opportunity — scientific validity:** when the minimum CV error used to choose
hyperparameters is also reported as final performance, use nested evaluation or
an untouched suitable test set for the complete selection procedure.

**Evidence and conditions:** demonstrated optimism in simulations,
[B32](sources.md#b32), Table 1 and Figs. 1–4. Nested CV reduces this selection
bias in the studied settings but remains variable and computationally costlier;
it does not repair dependent splits or deployment shift. Feature selection
([I06](#i06)) must also stay inside the fitted procedure.

### I34

**Align multiple-testing control with the discovery claim.**

**Scope:** statistics; inferred application to omics result tables.

**Opportunity — scientific validity:** when many hypotheses are screened with
an unadjusted per-test threshold but interpreted as a controlled discovery list,
define the tested family and use/report an appropriate multiplicity procedure.

**Evidence and conditions:** mathematical result and simulations,
[B33](sources.md#b33), §3, procedure (1) and Theorem 1. The original BH theorem
assumes independent test statistics; it is not a guarantee under arbitrary
dependence. FDR concerns the expected false fraction among rejections, not the
probability every retained hypothesis is true ([I29](#i29)).

### I35

**Report effect size and uncertainty alongside significance.**

**Scope:** statistics; inferred application to biological association reports.

**Opportunity — scientific validity:** when a results artifact treats a
thresholded p-value as effect magnitude or scientific importance, report the
estimated effect, suitable uncertainty, assumptions and selection context.

**Evidence and conditions:** interpretive limitation and expert guidance,
[B34](sources.md#b34), principles 3–6 and §4. A large p-value does not establish
absence of an important effect. Intervals and other alternatives also require
assumptions; changing the reporting format cannot repair a confounded study.

## Scientific software and workflows

### I36

**Check explicit data contracts.**

**Scope:** software; inferred application to biological matrix imports.

**Opportunity — robustness:** when assumed dimensions or identifiers are
unchecked, validate the required invariants and report actionable failures.

**Evidence and conditions:** recommendation, [S04](sources.md#s04), Box 1(5a),
and an observed error-contract repair in [S10](sources.md#s10): unsupported
time-index conversions receive explicit `TypeError`s rather than assertions.
Checks must encode justified requirements; overly strict checks reject valid
inputs. This detects violations, not scientific validity.

### I37

**Consolidate logic that must behave consistently.**

**Scope:** software; inferred application to repeated analysis steps.

**Opportunity — maintainability:** when equivalent operations are copied,
extract a shared function and verify preserved behavior.

**Evidence and conditions:** recommendation, [S04](sources.md#s04), Box 1(4b).
Duplication is not necessarily a bug. Consolidation helps when changes should
propagate; superficially similar operations may require different scientific assumptions.

### I38

**Optimize measured bottlenecks.**

**Scope:** software; inferred application to slow biological analyses.

**Opportunity — efficiency:** profile representative workloads, change the
dominant cost, and measure runtime/memory while checking required outputs.

**Evidence and conditions:** recommendation, [S04](sources.md#s04), Box 1(6a).
No speedup is established here. Workload dependence, numerical accuracy and
maintenance cost can outweigh a local optimization.

### I39

**Provide a usable interface description and executable example.**

**Scope:** software; documented scientific-computing guidance with a biological
data example, not a measured benefit for every bioinformatics package.

**Opportunity — maintainability and robustness:** when a script works only
through its author's tacit knowledge, document its purpose, inputs and use,
and provide a small example with a known expected result.

**Evidence and conditions:** recommendation, [S05](sources.md#s05), Software
development items 2a and 2i and the bird-count project example in Box 3. An
example helps users check installation and basic behavior; it is not comprehensive
validation. Keep its maintenance burden proportionate to the project.

### I40

**Preserve an executable path from inputs to results.**

**Scope:** software; documented bioinformatics workflow guidance.

**Opportunity — reproducibility:** when results depend on unrecorded edits or
commands, record input/code versions, parameters and transformations, automate
repeatable steps, and link outputs to the procedure that generated them.

**Evidence and conditions:** recommendation, [S06](sources.md#s06), rules 1–5.
For unavoidable manual steps, preserve an explicit record. Archiving every
intermediate may be impractical; retain what enables reconstruction and diagnosis.
A reproducible workflow can still implement an invalid analysis.

### I41

**Record and control stochastic execution.**

**Scope:** software and statistics; documented computational-research guidance,
with inferred application to resampling and clustering workflows.

**Opportunity — reproducibility:** when stochastic steps cannot be reconstructed,
record seeds and relevant generator/runtime settings, and expose randomness in
the run configuration.

**Evidence and conditions:** recommendation, [S06](sources.md#s06), rule 6.
The extension to generator/runtime metadata is this synthesis's qualification:
a seed alone need not guarantee identical parallel or cross-version execution.
Repeatability of one run is distinct from robustness across random realizations.

### I42

**Specify the environment actually used.**

**Scope:** software; inferred biological workflow application.

**Opportunity — reproducibility:** when setup ignores the required interpreter
or system libraries, encode and verify those requirements in a rebuildable recipe.

**Evidence and conditions:** observed reproduction failures and rescue changes,
[S07](sources.md#s07), §II(1–3), Tables I–II. Package pins alone are insufficient;
historical dependencies may become unavailable. No package manager guarantees success.

### I43

**Reuse environments only when their requirements match.**

**Scope:** software; inferred biological workflow application.

**Opportunity — efficiency:** when repeated setup dominates cost, reuse
environments keyed by compatible runtime and dependency requirements.

**Evidence and conditions:** reported optimization, [S07](sources.md#s07),
§II(4). Project identity alone is insufficient. The application must account for
other relevant platform/state differences; no isolated speedup is established here.

### I44

**Preserve argument grouping in setup wrappers.**

**Scope:** software; inferred biological workflow application.

**Opportunity — correctness:** replace token splitting that detaches an option
from its value with format-aware argument handling.

**Evidence and conditions:** observed requirements-installation defect,
[S07](sources.md#s07), §II(5). The example concerns editable dependency syntax;
preserving a line is not a general parser for every configuration grammar.

### I45

**Retain a reproducible regression for a confirmed defect.**

**Scope:** software; inferred application to scientific libraries and scripts.

**Opportunity — robustness:** when a fix lacks an executable witness, isolate
the faulty behavior and retain a relevant check that fails before and passes
after the change, alongside checks for unaffected requirements.

**Evidence and conditions:** operational examples from real-bug collections,
[S02](sources.md#s02), §2–3, and [S03](sources.md#s03), §2. These establish
an evidence pattern, not a measured causal benefit for every workflow. A passing
regression does not prove general correctness, and environment failures must
be distinguished from the intended defect.

## Data-processing software

### I46

**Distinguish logical types that share a storage representation.**

**Scope:** software/data handling; inferred application to biological metadata
with categorical and textual columns.

**Opportunity — correctness:** when dispatch relies on a broad storage-kind
test, distinguish logical types before choosing type-specific operations.

**Evidence and conditions:** observed defect, [S08](sources.md#s08),
`is_string_dtype` and `TestCategoricalDtype.test_not_string`: a categorical dtype
was classified as a string dtype. The upstream fix and regression were inspected,
not rerun. The classification must follow the intended API; this historical
example does not assert that current pandas behaves the same way.

### I47

**Preserve compound labels during indexing.**

**Scope:** software/data handling; inferred application to sample/condition or
other compound keys in biological tables.

**Opportunity — correctness:** when one tuple-valued label is mistaken for
multiple axis selectors, normalize the key according to the object's indexing
contract before checking dimensionality or accessing data.

**Evidence and conditions:** observed rejection of valid inputs,
[S09](sources.md#s09), `_AtIndexer._convert_key` and tuple/MultiIndex getter/setter
regressions. Interpreting a tuple as one label is appropriate only for interfaces
that define it that way. This preserves indexing semantics; it does not resolve
ambiguous biological identifiers ([I02](#i02)).

### I48

**Honor optional-return contracts on every execution branch.**

**Scope:** software; inferred application to analysis wrappers and table joins.

**Opportunity — correctness:** when one branch ignores a flag controlling
whether auxiliary outputs are returned, make its return structure consistent
with the documented request and check the relevant branches.

**Evidence and conditions:** observed defect, [S11](sources.md#s11),
`Index._join_multi` and `test_join_multi_return_indexers`: a join returned
indexers despite `return_indexers=False`. The inspected fix returns the index
alone in that case. Preserve the public contract rather than forcing a uniform
shape where an API intentionally permits several forms.

## Coverage and limits

This is a bounded, purposive synthesis. It is strongest on sequencing/omics and
Python-oriented scientific workflows. Some opportunities have one selected
source. No prevalence ranking, exhaustive bug taxonomy, or systematic-review
claim is made. The [method](research-method.md) records access limitations,
selection and consolidation decisions, and areas not covered. The
[source register](sources.md) distinguishes SERA's discovery role from evidence
supporting catalog entries.
