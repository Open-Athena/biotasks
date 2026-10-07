# Repository notebook-format coverage within the issue #5 inventory

Of the fixed 1,014 source identities, 871 have mapped GitHub repositories. All were checked at their previously recorded revisions: **405 contain detected notebook/literate-document formats**, 465 have none detected under this protocol, and 1 is unknown. The 143 unmapped sources are outside the repository denominator.

Detected formats occur in 21 of 22 original primary-domain labels (including infrastructure and general-purpose labels). The confirmed-detection fraction is 405/871 = 46.5%; this is not an estimate of notebook quality or population-wide biological coverage.

## Format counts

| Format | Repositories with detection |
| --- | ---: |
| Jupyter | 196 |
| R Markdown | 186 |
| Sweave/knitr | 37 |
| Quarto | 10 |
| marimo | 3 |
| Wolfram notebook | 3 |
| MATLAB Live Script | 1 |
| .NET Interactive | 1 |
| Jupytext | 1 |

Counts overlap across formats. Extension matches are not content validation; the marimo/Pluto/Jupytext signature probes are incomplete. Paired documents and rendered exports can be duplicates.

The scan performed 118 bounded text-prefix probes and left 100,836 other text files unprobed. It found 2,849 supported paths/signatures, not that many independent analyses.

## Primary domains

| Original primary domain | All sources | Mapped | Present | None detected | Unknown | Unmapped |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Bioimaging | 94 | 94 | 29 | 65 | 0 | 0 |
| Biomechanics & physiology | 1 | 1 | 1 | 0 | 0 | 0 |
| Biomedical text & clinical data | 23 | 22 | 4 | 18 | 0 | 1 |
| Cheminformatics & drug discovery | 45 | 44 | 21 | 22 | 1 | 1 |
| Computing infrastructure | 112 | 86 | 49 | 37 | 0 | 26 |
| Ecology & conservation | 4 | 4 | 4 | 0 | 0 | 0 |
| Gene expression | 48 | 35 | 22 | 13 | 0 | 13 |
| Gene regulation | 54 | 34 | 28 | 6 | 0 | 20 |
| General biology & multi-omics | 70 | 55 | 23 | 32 | 0 | 15 |
| Genetic variation | 51 | 47 | 17 | 30 | 0 | 4 |
| Genome assembly & annotation | 79 | 67 | 24 | 43 | 0 | 12 |
| Immunology | 12 | 11 | 5 | 6 | 0 | 1 |
| Metabolomics | 7 | 6 | 4 | 2 | 0 | 1 |
| Microbiome & metagenomics | 31 | 30 | 15 | 15 | 0 | 1 |
| Neuroscience & behavior | 48 | 48 | 22 | 26 | 0 | 0 |
| Phylogenetics & evolution | 24 | 21 | 7 | 14 | 0 | 3 |
| Protein structure & biophysics | 70 | 68 | 33 | 35 | 0 | 2 |
| Proteomics | 22 | 20 | 14 | 6 | 0 | 2 |
| RNA structure | 3 | 3 | 0 | 3 | 0 | 0 |
| Sequence processing | 94 | 79 | 12 | 67 | 0 | 15 |
| Single-cell & spatial omics | 67 | 54 | 39 | 15 | 0 | 13 |
| Systems biology & ontologies | 55 | 42 | 32 | 10 | 0 | 13 |

## Original ranking routes

Each route has 300 identities; membership overlaps between routes.

| Route | Mapped | Present | None detected | Unknown | Unmapped |
| --- | ---: | ---: | ---: | ---: | ---: |
| bioconda | 245 | 76 | 169 | 0 | 55 |
| bioconductor | 197 | 190 | 7 | 0 | 103 |
| pypi | 295 | 112 | 183 | 0 | 5 |
| github | 300 | 118 | 181 | 1 | 0 |

## Interpretation

This answers which parts of the previously selected software inventory have detectable notebook or literate-document files. It avoids choosing a few notebooks to create apparent breadth, but inherits the inventory selection and its assistant-assigned labels. Repository labels are not notebook-content labels. The supported formats include prose-oriented literate documents, so the positive set is a pool for further inspection, not a set of validated biological workflows.

None detected is not exhaustive absence: arbitrary text-notebook filenames, external links, other branches and submodules can be missed. Unknown tree responses remain explicit. Source revisions were fixed by the earlier study, while tree/prefix retrievals are new observations. No biological analyses were run.

See [protocol](README.md), [input provenance](input-provenance.json), [observations](observations.jsonl), [group CSV](domain-coverage.csv), [format CSV](domain-formats.csv) and [validation](validation.json).
