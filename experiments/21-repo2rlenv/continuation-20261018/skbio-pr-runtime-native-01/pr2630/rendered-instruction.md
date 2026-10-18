# Issue

**Title:** Sequence.lowercase() / FASTA+FASTQ `lowercase=` turn gaps and stop codons into control characters when the mask covers them (`-`→`\r`, `*`→`\n`)

## Description

### Description
Case conversion in `Sequence` flips bit 0x20 of characters that are not letters:

- `Sequence.lowercase(mask)`, which the FASTA/FASTQ writers use for their `lowercase=` option, XORs 0x20 into every selected character. **When a lowercase mask covers non-letter positions**, gaps, dots and stop codons become control characters (`-`→`\r`, `.`→`\x0e`, `*`→`\n`). Characters that are already lowercase become uppercase.
  - The usual read/write round trip (read with `lowercase='key'`, write with the same key) is not affected, because that mask only covers letters.
  - The problem appears with user-built masks, e.g. a region, interval or quality mask that spans gaps or stop codons.
- `Sequence(..., lowercase=True/'key')` treats every byte above `'Z'` as lowercase. In generic `Sequence` objects it therefore rewrites `[ \ ] ^ _ \` { | } ~` (e.g. `_`→DEL, `[`→`{`, `~`→`^`) and flags those positions as lowercase. For DNA, RNA and Protein these characters are invalid anyway, so only the error message is affected.

### Steps to reproduce
```python
import io
from skbio import DNA, Protein, Sequence

print(repr(DNA("AC-GT.N").lowercase([True] * 7)))      # 'ac\rgt\x0en'   expected 'ac-gt.n'
print(repr(Sequence("acgt").lowercase([True] * 4)))    # 'ACGT'          expected 'acgt'

fh = io.StringIO()
Protein("MKV*", metadata={"id": "p1"}).write(fh, format="fasta", lowercase=[False, True, True, True])
print(repr(fh.getvalue()))                              # '>p1\nMkv\n\n'  expected '>p1\nMkv*\n'

fh = io.StringIO()
DNA("ACGT-NNAC", metadata={"id": "s1"}).write(
    fh, format="fasta", lowercase=[False, False, True, True, True, True, False, False, False])
print(repr(fh.getvalue()))                              # '>s1\nACgt\rnNAC\n'  expected '>s1\nACgt-nNAC\n'

print(Sequence("AC_GT", lowercase=True).values.view("uint8"))  # [65 67 127 71 84] ('_' became DEL)
print(str(Sequence("A[B]", lowercase=True)))           # 'A{B}'
```
The protein FASTA above reads back as `Mkv`, so the stop codon is silently lost. The FASTQ writer behaves the same: `DNA('ACGT-NNAC', ...)` written with the mask above gives `'@s1\nACgt\rnNAC\n+\n...'`.

### Cause
`_sequence.py` uses `_ascii_lowercase_boundary = 90` (`self._bytes > 90`) to detect lowercase characters, and `^= 32` to convert, in both the constructor and `lowercase()`, without restricting either to ASCII letters.

### Proposed fix
Detect lowercase with `97 <= b <= 122`, and in `lowercase()` only convert selected bytes in `65..90`. I have a patch with tests and can open a PR.

Environment: scikit-bio main @ 4655b53 (code unchanged since ~0.4, present in 0.7.4), Python 3.14, NumPy 2.5.3, macOS arm64.

## Task

Modify the repository so that the issue described above is resolved. The task's test suite verifies your patch by applying it on top of the base commit `566dbe73c62a` and running the modified tests.