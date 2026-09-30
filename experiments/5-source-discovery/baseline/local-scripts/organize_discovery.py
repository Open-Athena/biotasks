import hashlib
import json
from pathlib import Path
import shutil

DOCS = Path('/home/exedev/.codex/worktrees/ec20/marin/docs/experiments')
DEST = DOCS / 'bio-task-generation/01-discovery'
VISUAL = Path('/home/exedev/.codex/visualizations/2026/09/29/01a0eece-d603-7e42-ae1b-92b907b8302a')
OLD_REPORT = DOCS / 'computational_biology_bioinformatics_packages.md'
OLD_DATA = DOCS / 'bio-repository-inventory.json'
assert not DEST.exists(), 'Discovery directory already exists; review before modifying it.'
report = OLD_REPORT.read_text()
payload = OLD_DATA.read_bytes()
data = json.loads(payload)
assert len(data['candidates']) == 95
before, rest = report.split('## Adoption correlation on the fixed 95-entry cohort\n', 1)
adoption, rest = rest.split('## GitHub topics observed in the existing cohort\n', 1)
topics, inventory = rest.split('## Candidate inventory\n', 1)

DEST.mkdir(parents=True)
(DEST/'data').mkdir()
(DEST/'figures').mkdir()
(DEST/'inventory.json').write_bytes(payload)

navigation = '''This directory contains results from source discovery, the first stage of
computational biology task generation for [issue #9257](https://github.com/marin-community/marin/issues/9257).
It accepts repositories and versioned source archives. The findings are discovery
evidence; no task authoring or execution validation is claimed.

| Page or artifact | Contents |
| --- | --- |
| [Inventory and source screening](#candidate-inventory) | The 95 candidates, their scientific uses and adoption measurements |
| [Adoption analysis](adoption.md) | Correlations, metric coverage, sensitivity checks and limitations |
| [GitHub topics](topics.md) | Observed topic strings, frequencies and search ideas |
| [Structured inventory](inventory.json) | Canonical records, provenance, dated observations and exact analysis results |
| [Adoption table](data/adoption-2026-09-29.csv) | Compact export of the 95 candidates and four adoption measures |

The stage number places discovery before source inspection, task authoring and
validation. Within this stage, filenames describe the artifacts. Observation
dates and cohort membership are recorded in the data and reports. Keep a dated
copy of the cohort and its measurements before replacing them with a larger
sample; comparisons between 95 and 200 candidates need both inputs.

## September 29, 2026 inventory

'''
before = before.replace('# Computational biology repository discovery\n\n', '# Source discovery\n\n'+navigation, 1)
before = before.replace('(bio-repository-inventory.json)', '(inventory.json)')
before = before.replace('The adoption comparison below finds little rank agreement between GitHub stars', 'The [adoption comparison](adoption.md) finds little rank agreement between GitHub stars')
before = before.replace('Results excluding entries with multiple package counters are reported below.', 'The [adoption analysis](adoption.md) also excludes entries with multiple package\ncounters as a sensitivity check.')
(DEST/'index.md').write_text(before+'## Candidate inventory\n'+inventory)

nav = '[Discovery inventory](index.md) · [Structured data](inventory.json)'
adoption_header = '''# Adoption analysis: September 29, 2026

'''+nav+'''

This analysis holds the existing 95 software candidates fixed. See the
[metric definitions and provenance](index.md#metrics-and-provenance) for source
dates, observation windows and package-to-source mapping.

[Download the adoption table](data/adoption-2026-09-29.csv).

![Adoption correlations for the fixed 95-candidate cohort](figures/adoption-correlations-2026-09-29.svg)

'''
(DEST/'adoption.md').write_text(adoption_header+adoption.lstrip())
topics_header = '''# GitHub topics: September 29, 2026

'''+nav+'''

Download the [repository topic lists](data/repository-topics-2026-09-29.csv)
or the [complete topic frequencies](data/topic-frequencies-2026-09-29.csv).

'''
(DEST/'topics.md').write_text(topics_header+topics.lstrip())

for source, target in [
    ('biology-adoption-95.csv', 'data/adoption-2026-09-29.csv'),
    ('biology-repository-topics.csv', 'data/repository-topics-2026-09-29.csv'),
    ('biology-topic-frequencies.csv', 'data/topic-frequencies-2026-09-29.csv'),
    ('biology-adoption-correlations.svg', 'figures/adoption-correlations-2026-09-29.svg'),
]:
    shutil.copyfile(VISUAL/source, DEST/target)
    assert hashlib.sha256((VISUAL/source).read_bytes()).digest() == hashlib.sha256((DEST/target).read_bytes()).digest()

assert (DEST/'inventory.json').read_bytes() == payload
assert OLD_REPORT.read_text() == report
assert OLD_DATA.read_bytes() == payload
OLD_REPORT.unlink()
OLD_DATA.unlink()
print('Moved local discovery results to', DEST)
print('Inventory sha256 unchanged:', hashlib.sha256(payload).hexdigest())
print('New files:', *[str(p.relative_to(DEST)) for p in sorted(DEST.rglob('*')) if p.is_file()], sep='\n')
