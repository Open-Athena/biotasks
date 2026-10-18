"""Validate the two reviewed scikit-bio reconstruction tasks before allocation."""
import json
from pathlib import Path
from history_runtime_input import check_task as check_recorded_task

REVIEWED = {
    'sha256:05a0a0b6a946e78c51b8b6848e6056474fd67df3f639701aba37132cef79c042': 'swe_smith',
    'sha256:5131392918c294ddbb1dbfa58e9e2f1d1105abaf3da077712d9bb74adce641d6': 'swe_flow',
}


def check_task(task: Path, review: Path):
    record = json.loads(review.read_text())
    recipe = REVIEWED.get(record.get('source_bundle_hash'))
    if recipe is None:
        raise ValueError('Unreviewed alpha-diversity bundle')
    check_recorded_task(task, review, allowed_recipes=(recipe,))
    contract = json.loads((task/'tests/contract.json').read_text())
    if contract['submitted_files'] != ['skbio/diversity/alpha/_base.py']:
        raise ValueError('Unexpected alpha-diversity submission contract')
    if len(contract['expected_passes']) != 34:
        raise ValueError('Unexpected alpha-diversity test contract')
