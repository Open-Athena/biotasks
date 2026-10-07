# Authoring sources behind rendered vignettes

Checked all 176 rendered-document locators across 96 source identities. Recovered 167 authoring documents: 88 R Markdown and 79 Sweave/knitr, spanning 94 sources. Authoring text was fetched and inspected; analyses were not executed. Direct sources are linked as primary LLM input, with rendered versions and extracted code retained as secondary representations. Source-level inventory totals are unchanged.

Nine documents remain unresolved across four sources:

- edgeR: edgeRUsersGuide. Its Rnw is a short wrapper including an existing PDF, not the guide authoring content.
- limma: usersguide. Its Rnw is likewise a PDF inclusion wrapper.
- lumi: IlluminaAnnotation, lumi, lumi_VST_evaluation and methylationAnalysis. Checked archive paths contain PDF/R representations but no matching literate authoring files.
- multtest: MTP, MTPALL and multtest. The archive includes MTP.tex, PDFs and an R script; original literate authoring source has not been established. The TeX file is retained as an unresolved lead in the archive inspection, not automatically promoted as authoring source.

The initial mirror became rate-limited; the main site returned access errors. The officially listed TU Dortmund mirror supplied the remaining accessible sources. All failures are retained. GlobalAncova uses lowercase .rnw filenames; snpStats/differences.Rnw is substantive prose without executable chunks. Neither should be omitted by a narrow detector. Sources are paired by release/path, not claimed to reproduce an earlier HTML build byte-for-byte.

The format chart counts source identities, not these document totals: 245 with R Markdown, 197 Jupyter, 77 Sweave/knitr, and four still with rendered-vignette fallbacks. Counts overlap for sources with several formats. A source can have both recovered authoring documents and unresolved rendered documents.

See summary.json for accounting, final-observations.jsonl for reconciled evidence, unresolved-archive-inspection.json for remaining archive paths, and validation.json for canonical grouping and unchanged identity checks. Intermediate observations remain preserved separately. Raw authoring text was inspected in memory; this pass saves locators and hashes, not a complete downloaded corpus.
