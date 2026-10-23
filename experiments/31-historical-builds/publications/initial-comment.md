🤖 Initial investigation is published on the permanent research branch at `0d9d4101de445f86f438ebb7182ab0463b9fd101`.

Verified original MACS evidence independently confirms extension removal in seven paired validations. An additional prerequisite emerged: three RUN commands in its saved reconstruction Dockerfile fail shell syntax checks. The original saved image cannot be assumed reproducible by building that recipe verbatim.

The saved Dockerfile replays failed transcript attempts, including trailing `</p>` text. Four saved rebuild commands are a separate potential procedure; unquoted `numpy>=1.25` and `Cython>=3.0` are shell redirections, not protected version constraints. Syntax-only checks do not execute recipes. A native-only rebuild would also leave emitted image/verifier lifecycle gaps, so complete oracle validation remains required.

Next: separate baseline reconstruction from historical rebuilding, then test correct-revision compilation at native and emitted-task boundaries before a MACS comparison. Saved rebuild commands exist but include shell-semantic hazards; no command or dependency repair has been applied.

[Evidence](https://github.com/Open-Athena/biotasks/blob/0d9d4101de445f86f438ebb7182ab0463b9fd101/experiments/31-historical-builds/findings.md) · [Scope](https://github.com/Open-Athena/biotasks/blob/0d9d4101de445f86f438ebb7182ab0463b9fd101/experiments/31-historical-builds/issue-scope.md) · [Logbook](https://github.com/Open-Athena/biotasks/blob/0d9d4101de445f86f438ebb7182ab0463b9fd101/experiments/31-historical-builds/logbook.md). All changes remain research-only; no promotion to main, live task repair or model spend. The issue remains open.
