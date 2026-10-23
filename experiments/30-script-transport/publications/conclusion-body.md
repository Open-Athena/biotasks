Can a general transport change remove large-script argument failures without changing native validation behavior? Follow-up to #28. **The bounded comparison is complete; this issue remains open for user review. No production change promoted.**

**Result:** the stdin candidate removes the reproduced Linux `E2BIG` error for Matchms PR958's 425,528-byte post-fix script. Successful control PR671 preserves exactly the same native sets under both transports: 1 fail-to-pass and 30 pass-to-pass tests. Earlier real-Docker probes also verified exact delivery of a 1,080,000-byte payload.

**No recovered task for PR958:** both delivered stages collect zero tests because unchanged upstream targeting includes two files deleted by the patch. This separate failure is tracked in #32. No patch reduction, dependency/test repair, parser change or extra model call was used.

**Limits:** the saved recipe was reconstructed, so mutable dependency drift remains; original failed script bytes were not retained. Both transports leave remote commands alive after client timeout; the comparison aborts timed-out arms and removes their containers. Shell diagnostic/introspection differences remain. Native validation is distinct from exports and independent Harbor controls.

**Accounting and retention:** all five attempts are terminal, totaling 0.25515 allocated CPU-hours on existing reserved capacity, zero model calls. Owned containers/images/cache and tools were removed and absence verified. Raw Matchms evidence has verified private local archive readback; the remote archive has a seven-day TTL.

[Live diagnosis](https://github.com/Open-Athena/biotasks/blob/4862b97e/experiments/30-script-transport/live-diagnosis.json) · [Verified archive and cleanup](https://github.com/Open-Athena/biotasks/blob/4862b97e/experiments/30-script-transport/live-readback.json) · [Findings and limitations](https://github.com/Open-Athena/biotasks/blob/4862b97e/experiments/30-script-transport/findings.md) · [Scope](https://github.com/Open-Athena/biotasks/blob/4862b97e/experiments/30-script-transport/issue-scope.md). Detailed logs remain in comments.
