# Classification rules v0.2

These are working rules for the pilot, not a finalized ontology.

## Field versus setting

Assign a field when it describes the analysis objective or biological interpretation,
not merely the material's origin. More than one field is allowed; do not force a
single primary field. Tissue, organism, disease and cell origin remain separately
searchable setting metadata.

- A PBMC workflow that clusters expression and tests markers can be Transcriptomics,
  with immune cells recorded as setting. Do not automatically assign Immunology.
- Immune receptor clonotypes, immune-population identification and immune function
  can support Immunology. Gene-expression analysis in the same notebook can also
  support Transcriptomics, with separate evidence for each.
- Bioimage analysis is retained as a pragmatic browse field for imaging methods.
  Assign Cell and developmental biology additionally only when the analysis asks
  about cellular organization, differentiation, development or another cellular
  biological process. Generic nucleus masks alone do not justify that field.
- Plant or human sample origin does not create a new field automatically. Organism
  filters support these use cases without duplicating every analytical category.

These boundaries deliberately prefer fewer supported labels to automatic inheritance.
They can be revised if a broader sample shows that browsing becomes unintuitive.
The field vocabulary is a navigation vocabulary, not a disjoint scientific ontology.

## Infrastructure and source role

Keep scientific field and source role separate. A cloud-access demonstration can
operate on genomic data without performing genomic inference. Record access,
format-conversion or visualization operations where actually present. A wholly
general storage tutorial can have field status `not_applicable`; an ambiguous one
has `insufficient_evidence`. Neither is the same as `unreviewed`.

Repository records describe declared scope at a pinned revision. Notebook records
describe inspected content. Relations distinguish `hosted_by`, `uses_tool` and
`documents_project`. Tool/project resolution can be incomplete without transferring
labels from the nearest repository. A repository's observed notebook coverage is
a derived, explicitly partial view, not its declared scope.

## Operation evidence

An operation assignment needs both a role and execution-form information:

- `implemented`: concrete analysis code is present. Record disabled/demo/commented
  code where applicable; this status never means the notebook was executed.
- `exercise`: instructions ask the learner to implement or invoke it.
- `discussed_only`: explanation or suggestion without performing/requesting it.
- `upstream_supplied`: inputs include results of the operation.

A notebook may contain more than one role for the same operation. Count each
notebook once per label and role; do not sum those counts as independent notebooks.
Absence of an annotation is not evidence that an operation is absent unless a
specific reviewed rejection is recorded. Selected-operation review is not an
exhaustive inventory of every import, plot or data manipulation.

## Denominators and provenance

Count unique canonical document identities, deduplicating authoring/rendered
representations before aggregation. Keep suggested, content-supported and disputed
assignments separate. Show review coverage for each facet; a reviewed notebook may
have a supported modality but insufficient biological field evidence.

Data modality describes the observation/input kind. Keep assay subtype, processing
stage, biological setting and observed/adapted/simulated/predicted origin separately.
Unspecified assay does not mean unspecified data: metabolite tables can be labeled
without guessing mass spectrometry. Simulation trajectories do not establish that
the notebook runs simulations. Source-described provenance is not independently
verified dataset provenance.

The pilot is not a corpus-wide classification pass. Do not divide its sample size
by the full notebook inventory before identity reconciliation. No task competence
is claimed until the task requires and independently verifies the corresponding work.
