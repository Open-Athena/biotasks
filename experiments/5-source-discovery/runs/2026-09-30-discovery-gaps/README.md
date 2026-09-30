# Known-repository discovery audit

The user asked for gaps found using knowledge of popular computational biology
repositories after Evo 2 was shown to be absent from the discovery pool. Freeze
an assistant-nominated reference panel before checking it against the saved pool
or fetching current metadata. Include known positive controls and nominees from
DNA/protein models, single-cell analysis, genomics, molecular simulation,
imaging/neuroscience, phylogenetics/ecology and biological workflow tools.

This purposive panel is a diagnostic, not a random sample, exhaustive inventory,
or unbiased estimate of recall. Evo 2 prompted it; AlphaFold 2 and 3 were already
known manual additions. Other names and areas reflect assistant prior knowledge;
canonical identities and current status must be checked. Names/areas are not a
new scientific eligibility or licensing approval. Do not add nominees to the
frozen rankings or recompute the explorer's scientific results.

Distinguish absence from the 1,370-source GitHub candidate pool, absence from the
672-source four-list union, explicit exclusions, and candidates below selection
cutoffs. Resolve aliases before joining. Current stars are a new snapshot, not
historical measurements; compare with the saved 889-star cutoff only to prioritize
investigation, never assign retrospective ranks.

Budget: public GitHub metadata for at most 150 nominees in sequential batches;
at most 20 targeted search probes and primary-source README inspections for
misses. No model calls, candidate execution, biological data download or paid
compute. Local analysis is standard-library Python, estimated below 100 MiB,
under the shared resource guard. Record query inputs, exact source checkpoint,
observations, timestamps, hashes, decisions and limitations. Checkpoint the
nominees and executable collector before collection. Preserve raw errors rather
than interpreting unresolved names as discovery misses.

## Findings

All 112 intended repositories resolved after three explicit spelling/ownership
corrections. Of this purposive panel, 75 are in the saved GitHub pool and 37 are
absent. Eleven absent repositories currently exceed the saved 889-star selection
cutoff; all eleven are also absent from the four-list union. Another 23 panel
repositories are in the pool but below its GitHub cutoff, including HyenaDNA,
scVelo and FreeSurfer. Those are selection-depth cases rather than discovery
misses. The panel contributes 62 sources already in the four-list union. These
counts describe this nominated panel only, not population-wide recall.

| Absent repository | Current stars | Discovery evidence / likely gap |
| --- | ---: | --- |
| [Project-MONAI/MONAI](https://github.com/Project-MONAI/MONAI) | 8,733 | `medical-imaging` fails; its `medical-image-processing` topic matches. |
| [ArcInstitute/evo2](https://github.com/ArcInstitute/evo2) | 4,237 | `genomics` fails; `genome` matches. |
| [aqlaboratory/openfold](https://github.com/aqlaboratory/openfold) | 3,435 | `protein` fails; its `protein-structure` topic matches. |
| [RosettaCommons/RFdiffusion](https://github.com/RosettaCommons/RFdiffusion) | 3,068 | Sparse description and no topics; a `protein` README search matches. |
| [Biohub/esm](https://github.com/Biohub/esm) | 2,980 | No description or topics; a `protein` README search matches. EvolutionaryScale/esm redirects here. |
| [RosettaCommons/RoseTTAFold](https://github.com/RosettaCommons/RoseTTAFold) | 2,268 | Model-name description and no topics; a `protein` README search matches. |
| [bytedance/Protenix](https://github.com/bytedance/Protenix) | 2,066 | `molecular` fails; `biomolecular` matches. |
| [chaidiscovery/chai-lab](https://github.com/chaidiscovery/chai-lab) | 2,000 | `biomolecular` matches; this term was omitted. |
| [nf-core/rnaseq](https://github.com/nf-core/rnaseq) | 1,378 | `rna` matches; RNA/rna-seq vocabulary was omitted. |
| [stardist/stardist](https://github.com/stardist/stardist) | 1,273 | `bioimaging` fails; its `bioimage-analysis` topic matches. |
| [mikolmogorov/Flye](https://github.com/mikolmogorov/Flye) | 951 | Assembly/single-molecule/sequence vocabulary is absent from the 24 terms; no topics. This explanation is inferred from current metadata. |

Sixteen targeted [search probes](probe-results.json) reproduce the proposed
matching distinctions using the live GitHub index. Literal substring matches in
`audit.json` are only a diagnostic: they do not model GitHub search behavior.
OpenFold and Protenix illustrate why substring checks would be misleading. The
probes and current metadata support these explanations but cannot reconstruct
historical metadata or search-index state on September 29. Current star counts
are not inserted into the old rankings.

The missing high-star set spans healthcare imaging, DNA/protein foundation
models, RNA workflows and assembly. This is broader than a one-repository
exception. Candidate discovery should include explicit vocabulary variants and
compound topics, a separately screened README-search pass for poorly described
repositories, and a stable known-source reference panel. Keep human/assistant
seeds marked separately from query-derived candidates so their contribution can
be measured. Increasing the cutoff alone cannot recover absent candidates.

The three initial invalid names were corrected using primary repository pages
in [identity-corrections.json](identity-corrections.json), not counted as misses
until resolved. Raw initial observations, errors and the first analysis remain
in this directory. Candidate identities were joined case-insensitively using
both requested aliases and API-resolved canonical names; duplicate repository
IDs would stop analysis. None were found.

## Reproduction and limits

`audit.py collect` fetched the predeclared panel in four sequential GraphQL
batches from source checkpoint `19791fc`. `collect-corrections` and `probe`
used checkpoint `c062369`; `analyze` joins the preserved CSVs offline and records
their SHA-256 hashes in [audit.json](audit.json). Query/response files and
observation timestamps are retained. All calls used public metadata and the
normal elevated GitHub CLI; there were no model calls or candidate executions.
Python 3.13.13, standard library only.

Use `python3 experiments/5-source-discovery/scripts/run_bounded.py 100` before
`.venv/bin/python experiments/5-source-discovery/runs/2026-09-30-discovery-gaps/audit.py ACTION`.
Run `analyze` to reproduce from saved observations. Collection actions contact
GitHub and would overwrite observation files; run a copy in a new directory to
collect another snapshot. The [initial collection](collection.txt),
[corrections](corrections.txt), [probes](probe-checks.txt) and
[final analysis](analysis.txt) include start/end, exit and resource records.
The missing list is a research-prioritization result, not a new eligibility,
license or execution approval.
