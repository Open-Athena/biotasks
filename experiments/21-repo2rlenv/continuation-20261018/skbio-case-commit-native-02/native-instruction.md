# Issue

**Title:** BUG: restrict Sequence case conversion to ASCII letters

## Description

Sequence.lowercase() flipped the case bit (0x20) of every selected
character. When the mask covered non-letter positions, gaps, dots and
stop codons became control characters ('-' -> '\r', '.' -> '\x0e',
'*' -> '\n'), and lowercase letters were uppercased. The FASTA and FASTQ
writers use this method for their `lowercase` option, so such masks
silently produced corrupted files.

The `lowercase` constructor parameter treated every byte above 'Z' (90)
as lowercase, so '[', '\\', ']', '^', '_', '`', '{', '|', '}' and '~'
were rewritten in generic Sequence objects (e.g. '_' became DEL) and
flagged as lowercase.

Only convert A-Z to lowercase and a-z to uppercase.

## Task

Modify the repository so that the issue described above is resolved. The task's test suite verifies your patch by applying it on top of the base commit `566dbe73c62a` and running the modified tests.