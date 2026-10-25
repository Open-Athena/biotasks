# Current converter on the ten original development inputs

All ten original notebook payloads pass deterministic repeat conversion and the converter’s ordered Python AST-equivalence check. Each original input hash is verified against its frozen payload and source manifest. Code-cell counts match the original inventory; Markdown is retained as comments and stored outputs are excluded. [Summary and per-source receipts](current-conversion/summary.json).

This is **conversion evidence only**. No notebook computation, dependency installation, model, host or task sandbox ran. It does not establish reference execution, scientific fidelity, grader validity or release readiness.

The check ran from commit5c609f47 with Python3.13.13 and the checkout’s locked Jupytext environment. Exit0,0.64seconds,67,952KiBpeakRSS under the shared-node resource guard. Original invalid-escape syntax warnings were reported during parsing; no source statements were edited. The first attempt hit a local reporting error because an arbitrary source ID was used as a filename. Its partial receipts and failure record remain preserved; the rerun uses an ordinal and source digest, with no converter or source change.

Command:

```bash
PYTHONPATH=src python /tmp/biotasks19-resource-guard.py 120 .venv/bin/python experiments/19-repo2rlenv-notebook-pilot/panel-rounds/053/check_original_conversions.py --private-root /home/exedev/.local/share/biotasks/handoffs/issue-19 --inputs experiments/19-repo2rlenv-notebook-pilot/panel-rounds/049/common-input-readiness.json --output experiments/19-repo2rlenv-notebook-pilot/panel-rounds/053/current-conversion
```

The private-root argument locates existing original input archives; no credentials or private data are copied into these reports. Temporary extracted source files are removed after each conversion.
