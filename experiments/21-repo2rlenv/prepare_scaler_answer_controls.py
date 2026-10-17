"""Prepare independent answer-format and incorrect-answer controls, without grading."""
import argparse
import hashlib
import json
import re
from pathlib import Path


def prepare(tasks):
    controls = []
    for task in sorted(tasks.iterdir()):
        if not task.is_dir():
            continue
        expected = json.loads((task / 'tests/reference.json').read_text())
        # These fixtures have independently audited exact nonnegative integer answers.
        match = re.fullmatch(r'\\boxed\{(0|[1-9][0-9]*)\}', expected)
        assert match is not None, 'Unexpected reference representation'
        value = int(match.group(1))
        for name, answer, reward in [
            ('equivalent_decimal', f'{value}.0\n', 1),
            ('equivalent_scientific', f'{value}e0\n', 1),
            ('wrong_off_by_one', f'{value + 1}\n', -1),
            ('invalid_text', 'unknown\n', -1),
        ]:
            controls.append({'task': task.name, 'case': name, 'answer': answer,
                             'expected_reward': reward,
                             'reference_sha256': hashlib.sha256((task / 'tests/reference.json').read_bytes()).hexdigest(),
                             'grader_sha256': hashlib.sha256((task / 'tests/grade.py').read_bytes()).hexdigest()})
    return {'stage': 'prepared_not_executed', 'cases': controls,
            'model_calls': 0, 'task_assets_modified': False,
            'reward_range': [-1, 1],
            'purpose': 'Execute unchanged native graders on independent equivalent and incorrect answers, then compare a representative Marin conversion.',
            'limitations': ['These controls are grader checks, not blind solver attempts or additional tasks.']}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--tasks', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.write_text(json.dumps(prepare(args.tasks), indent=2) + '\n')
