# Issue

**Title:** BUG: restrict Sequence case conversion to ASCII letters

## Description

.

`Sequence.lowercase()` flipped the case bit (0x20) of every selected character, so a mask covering non-letters turned gaps, dots and stop codons into control characters (`-` → `\r`, `.` → `\x0e`, `*` → `\n`) and turned lowercase letters uppercase. The FASTA and FASTQ writers use this method for their `lowercase=` option, so such masks silently wrote corrupted files.

The `lowercase=` constructor parameter treated every byte above `Z` as lowercase, so ``[ \ ] ^ _ ` { | } ~`` were rewritten in generic `Sequence` objects (e.g. `_` became DEL) and flagged as lowercase.

Case conversion is now restricted to `A-Z` / `a-z`:

- `lowercase()` only sets the case bit on `A-Z` at the selected positions; everything else is left as is.
- The constructor's lowercase mask only covers `a-z`.

`DNA("AC-GT.N").lowercase([True] * 7)` now gives `'ac-gt.n'` (was `'ac\rgt\x0en'`).

Tests added for `Sequence.lowercase`, the constructor, and the FASTA/FASTQ writers with masks spanning gaps and stop codons. `skbio/sequence` and the FASTA/FASTQ test modules pass locally. The only failures are 15 doctests that fail identically on `main` in my environment.

Please complete the following checklist:

* [x] I have read the [contribution guidelines](https://scikit.bio/contribute.html).

* [x] I have documented all public-facing changes in the [changelog](https://github.com/scikit-bio/scikit-bio/blob/main/CHANGELOG.md).

* [ ] **This pull request includes code, documentation, or other content derived from external source(s).** If this is the case, ensure the external source's license is compatible with scikit-bio's [license](https://github.com/scikit-bio/scikit-bio/blob/main/LICENSE.txt). Include the license in the `licenses` directory and add a comment in the code giving proper attribution. Ensure any other requirements set forth by the license and/or author are satisfied.

  - **It is your responsibility to disclose** code, documentation, or other content derived from external source(s). If you have questions about whether something can be included in the project or how to give proper attribution, include those questions in your pull request and a reviewer will assist you.

* [x] This pull request does not include code, documentation, or other content derived from external source(s).

Note: [This document](https://scikit.bio/devdoc/review.html) may also be helpful to see some of the things code reviewers will be verifying when reviewing your pull request.

## Task

Modify the repository so that the issue described above is resolved. The repository is checked out at base commit `566dbe73c62a`. Edit files in place; the verifier captures your changes via `git diff` and scores them against an oracle patch using SWE-RL-style diff-similarity reward.