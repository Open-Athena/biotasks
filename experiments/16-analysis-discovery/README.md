# Analysis discovery — ongoing research

Issue: https://github.com/Open-Athena/biotasks/issues/16

The user retains the completion decision. Keep this experiment and issue open
until they are satisfied. This research branch is not intended for merging.

- [Current HTMLPreview](https://htmlpreview.github.io/?https://github.com/Open-Athena/biotasks/blob/45f74e7216afe0e1bb45c7cba81de5750301527c/experiments/16-analysis-discovery/workbench.html) (methods-first workbench; public browser checks passed)
- [Latest source recovery and input tracing](resolution.md)
- [First 100-candidate checkpoint](expansion.md) (91 inspected at that time)
- [Original 40-candidate findings](findings.md) (frozen checkpoint)
- [Interactive explorer](explorer.html), self-contained and usable offline
- [Candidate manifest](candidates.json) and [CSV](candidates.csv)
- [Protocol](protocol.md), [logbook](logbook.md), [computed summary](summary.json)
- [Awesome-biology link inventory and traced paths](evidence/awesome-biology.json)

Regenerate the summary, CSV, HTML and input checksums with the standard library:

```bash
python3 experiments/16-analysis-discovery/build_explorer.py
```

This validates unique IDs/canonical URLs/known aliases, required assessment
fields, evidence paths, allowed taxonomy, no-execution state and source hashes
against retrieval metadata. It calculates counts, multilabel coverage, descriptive
workflow lists, study concentration and each main route's exclusive subdomains.
It does not execute any discovered analysis or make network requests.

`inspect_github.py` and `inspect_kaggle.py` document the earlier static source
retrievals. They access current remote sources and write temporary inspection
text plus metadata, so rerunning them is a new acquisition, not offline
reproduction of frozen evidence. Preserve the current evidence before any rerun.
GitHub inspection requires ordinary authenticated `gh`; follow AGENTS.md for
elevated CLI execution. No credentials are included here.

`browser_check.py` checks filters, coverage drilldowns, CSV contents, source
details, empty states and desktop/mobile layout using Playwright and Chromium.
It accepts an optional public HTMLPreview URL. Its environment paths reflect the
shared VM used for this snapshot; adapt them on another machine. Follow the
shared-node resource checks and nonblocking lock in AGENTS.md for browser work.
No browser environment was added to the supported project dependencies.

Search evidence preserves query metadata and returned document titles/URLs.
Web reader text was intentionally omitted, and timestamps are unavailable for
some later calls; their observation date is 2026-10-06. Candidate annotations
supply concise factual observations. GitHub/Kaggle source hashes support identity
checking without redistributing full notebooks; rendered-page versions remain a
limitation. `manifest-sha256.json` hashes the small evidence and builder inputs.

HTMLPreview publication uses a Git commit permalink rather than a moving branch.
The explorer embeds its data and has no external script, font or data dependency.
Publication is a review checkpoint, not scientific validation or issue completion.

Build the current methods-first presentation after regenerating the explorer data with `python3 experiments/16-analysis-discovery/build_workbench.py`. The historical design comparisons remain separate.

The [fixed issue-5 repository audit](repo-notebook-audit/results.md) checks multiple notebook/literate-document formats across 871 mapped repositories. Its original 1,014-source universe and labels are separate from the 100-document collection.
