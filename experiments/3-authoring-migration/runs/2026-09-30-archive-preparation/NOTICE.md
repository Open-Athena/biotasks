# Research-cache attribution and limits

This collection preserves authoring research evidence. Project-generated
prompts, inventories, reviews and logs retain their recorded scientific
limitations. Third-party source copies retain their own terms; this aggregate
does not relicense them under BioTasks' root license. The cache contains source
and documentation material, not a released biological dataset or executable
task corpus.

| Cached material | Source and recorded terms | Accompanying notice |
| --- | --- | --- |
| Scanpy source/notebook and notebook-cell extraction | scverse/scanpy, pinned review revision `8c1463d5d97272d5811ad3f4efb57483e23b4c7e`; BSD 3-Clause | `notices/scanpy.txt` |
| STAR-DESeq2 workflow scripts, rules and example configuration | snakemake-workflows/rna-seq-star-deseq2 at `aa6b17edf3396230165c18709d04cd982bdaaa4c`; MIT | `notices/star-deseq2.txt` |
| MMseqs2 README and command-registration source | soedinglab/MMseqs2 at `564f40d8857f4eca4e1dfe100c67c155b1933e70`; MIT | `notices/mmseqs2.txt` |
| DESeq2 source, vignette, manual and tests | thelovelab/DESeq2 at `c62c60c6ff83fd84ce115cacd1c49827533f85a7`; DESCRIPTION says LGPL >=3 | `notices/deseq2-description.txt`, `notices/LGPL-3.txt`, `notices/GPL-3.txt` |
| rnaseqGene workflow vignette | thelovelab/rnaseqGene at `0d7e27dde3ca9875cf94770ed9de35e346dd3676`; Artistic 2.0 | `notices/rnaseqGene-description.txt`, `notices/Artistic-2.0.txt` |

Source-review files are unmodified bytes. The local `sources.json`, run records,
source URLs and hashes retain the historical provenance that was available.
Some older cache files do not record an exact retrieval revision; the pinned
notice review does not retroactively fill that gap. Raw execution logs contain
public-source retrievals and excerpts at their original URLs. They are evidence,
not a supported software distribution, benchmark grade or model reasoning
export. Partial results, failed starts and service errors are retained.

Six UCSC files are excluded from the proposed public bundle and remain at
their original source-cache paths. The pinned root notice and liftOver override
are included only to document this exclusion. liftOver has custom terms;
downloaded catalog/help surfaces and directory-specific overrides require
further review before redistribution. No UCSC executable or biological data
asset is included. A future decision must preserve the original hashes and
record any new destination and its access terms.

License notices were captured during migration, separately from historical
research retrievals. `notices/sources.json` gives their pinned source URLs.
The GPL/LGPL text comes from the VM's standard `/usr/share/common-licenses/`;
Artistic 2.0 comes from GitHub's public license API. Preserve these notices with
the archive. No credential or environment file belongs in this collection.
