<!-- Adapted from Marin 72008dd68247318a367a840a4f41e27fb15ff7e1:docs/experiments/bio-task-generation/index.md.
Migration changes are documented in docs/migration.md. -->

# Reference cases

Revisit these examples when changing discovery, recipe extraction, instance generation or validation. They are reference cases for diagnosing the pipeline and reviewing task framing, not a ranked source list or a requirement to implement every example now.

| Reference case | What to examine when the pipeline changes |
| --- | --- |
| [Scanpy tutorial](https://scanpy.readthedocs.io/en/stable/tutorials/basics/clustering.html), with our [recipe discussion](examples/transcriptomics.md#scanpy-focused-and-integrated-recipes) | Extract focused and integrated tasks from a teaching workflow; distinguish numerical verification from open-ended interpretation |
| [Snakemake STAR–DESeq2 workflow](https://snakemake.github.io/snakemake-workflow-catalog/docs/workflows/snakemake-workflows/rna-seq-star-deseq2.html), with our [worked example](examples/star-deseq2.md) | Use rule boundaries and dependencies; preserve scientific decisions while composing stages and subsetting data |
| Gonzalo Benegas's [papers](https://gonzalobenegas.github.io/), [Scholar profile](https://scholar.google.com/citations?user=tJbZmiUAAAAJ) and [repositories](https://github.com/gonzalobenegas) | Find useful tasks in paper-specific code with varying documentation and portability; obtain feedback from a researcher familiar with the original scientific intent |
| [Tim O'Donnell's work](https://timodonnell.github.io/) | Add collaborator-familiar papers and software as further cases for reviewing scientific task framing; select specific examples as the pipeline develops |
| [bedtools](https://bedtools.readthedocs.io/en/latest/) | Review genomic interval operations and their composition into scientific workflows |
| [UCSC Genome Browser binaries](https://hgdownload.soe.ucsc.edu/admin/exe/), with their [source code](https://github.com/ucscGenomeBrowser/kent/tree/master/src/utils) | Review tasks built around standalone command-line utilities, including their input/output conventions |

Gonzalo Benegas has substantial experience using bedtools and the UCSC Genome Browser binaries. Use that familiarity to guide manual review of their task framing and expected outputs.

For a proposed pipeline change, compare the resulting question, recipe boundary, input adaptation, meaningful instance variation and deterministic grading contract on the affected cases. Check whether the framing preserves the scientific work and whether source-code limitations are being confused with lack of scientific value. Record concrete examples and unresolved questions for review. Author feedback informs this review; it does not serve as grading-time judgment.

These reference cases provide a starting point for manual review. They do not yet form an automated regression suite or provide exhaustive coverage. Inspect and develop them as the relevant pipeline stage takes shape. Versions used for actual comparisons should be pinned; additional cases can be added when they expose a different failure mode.
