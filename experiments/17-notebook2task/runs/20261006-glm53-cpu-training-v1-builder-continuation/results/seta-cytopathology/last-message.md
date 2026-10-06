The complete Harbor task package is written to `/app/work/seta-cytopathology`. Final structure:

```
seta-cytopathology/
├── environment/
│   └── Dockerfile          # python:3.12-slim, pinned sci env, uv+tmux, COPY data/data.csv → /app/data/data.csv
├── instruction.md          # Agent-visible brief only (published protocol, schemas, acceptance criteria)
├── solution/
│   ├── solve.sh            # installs + runs the pipeline, sanity-checks artifacts
│   └── run_pipeline.py     # full fixed-protocol comparison (oracle implementation)
├── task.toml               # medium, 1 CPU / 2G, verifier 900s, agent 3600s
├── tests/
│   ├── test.sh             # preinstalled python3+pytest, JUnit XML, reward.txt, preserves pytest status
│   └── test_outputs.py     # 9 independent verifier tests
├── weights.json            # 9 tests, sums to exactly 1.00
└── judge_report.md         # PASS, all runtime checks marked NOT RUN
```

Key design decisions, per the explicit recipe contract:

- **Fixed protocol, published config**: split/fold seeds (20250607), model identifiers, hyperparameters, label mapping, tie-break, and tolerances are agent-visible in `instruction.md`; the verifier compares numerical outputs, never code.
- **Independent regeneration**: `tests/test_outputs.py` reads only its trusted `tests/data.csv` (located relative to `__file__`, staged by parent), regenerates split/folds, refits the three declared native algorithms with one worker, and compares OOF/test probabilities at 1e-6 (rtol=0). It never imports solver code, trusts solver metrics/folds, or relies on `folds.csv` (optional-but-validated).
- **Adversarial coverage without vacuous meta-tests**: the leaky-preprocessing discrimination guard is embedded inside `test_probabilities_match_reference` (which inspects solver artifacts and fails on empty); perfect-label, shuffled-id, fabricated-metric, and empty submissions all fail the graded assertions themselves.
- **Honest artifacts**: the oracle writes full-precision (`%.17g`) predictions, then recomputes every metric in `metrics.json` from the emitted CSVs; selection uses mean training-fold ROC-AUC only.
- **Data staging**: no `data.csv` authored anywhere; Dockerfile reads `data/data.csv` relative to the environment build context only — never `tests/` or `solution/`.

All runtime claims (Docker build, oracle/nop harbor runs, runtime and peak-memory measurement, 1e-6 tolerance discrimination) are recorded as **NOT RUN** in `judge_report.md` for parent validation on remote CPU.