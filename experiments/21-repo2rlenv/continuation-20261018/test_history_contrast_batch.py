"""Small synthetic checks; never clone repositories, create workers or call models."""

import json
import io
import tarfile
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from history_contrast_batch import run_batch
from contrast_summary import summarize
from run_mutation_trc import recipe_arguments


class HistoryContrastBatchTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.output = Path(self.temporary.name) / 'output'
        self.config = {'recipe': 'r2e_gym', 'options': {
            'history_limit': 1, 'max_candidates': 1, 'target': 1,
        }}
        self.candidate = {'id': 'a' * 20, 'head': 'b' * 40}

    def prepare(self, candidates, rejected=()):
        def generate(config, destination):
            destination.mkdir(parents=True)
            record = {'attempted': len(candidates) + len(rejected),
                      'candidates': candidates, 'rejected': list(rejected),
                      'repo_revision': 'b' * 40, 'repository_cache': '/fixture/cache'}
            (destination / 'generation.json').write_text(json.dumps(record))
            return record
        return generate

    def test_native_context_forwarded_and_selection_retained(self):
        contrast = {**self.candidate, 'contrast': {'FAIL_TO_PASS': ['test_one']}}
        evaluate = Mock(return_value=contrast)
        result = run_batch(self.config, self.output, self.prepare([self.candidate]), evaluate)
        forwarded, destination = evaluate.call_args.args
        self.assertEqual(forwarded['candidate'], self.candidate)
        self.assertEqual(forwarded['options'], self.config['options'])
        self.assertEqual(forwarded['repository_cache'], '/fixture/cache')
        self.assertEqual(destination, self.output / 'candidates' / self.candidate['id'])
        self.assertEqual(result['candidates'], [contrast])
        original = json.loads((self.output / 'selection/generation.json').read_text())
        self.assertEqual(original['candidates'], [self.candidate])
        self.assertEqual(json.loads((self.output / 'generation.json').read_text()), result)

    def test_source_rejection_is_charged_without_evaluation(self):
        rejected = [{'head': 'c' * 40, 'reason': 'source_filter'}]
        evaluate = Mock()
        result = run_batch(self.config, self.output, self.prepare([], rejected), evaluate)
        evaluate.assert_not_called()
        self.assertEqual(result['attempted'], len(rejected))
        self.assertEqual(result['rejected'][0]['head'], rejected[0]['head'])
        self.assertEqual(result['candidates'], [])

    def test_contrast_failure_preserves_identity_and_original_selection(self):
        result = run_batch(self.config, self.output, self.prepare([self.candidate]),
                           Mock(side_effect=RuntimeError('fixture failure')))
        self.assertEqual(result['rejected'][0]['id'], self.candidate['id'])
        self.assertEqual(result['rejected'][0]['error_type'], 'RuntimeError')
        self.assertEqual(result['selected_not_evaluated'], [])
        self.assertEqual(result['candidates'], [])
        self.assertTrue((self.output / 'selection/generation.json').is_file())

    def test_scan_bound_rejected_before_any_native_work(self):
        self.config['options']['history_limit'] = 2
        prepare, evaluate = Mock(), Mock()
        with self.assertRaisesRegex(ValueError, 'History scan'):
            run_batch(self.config, self.output, prepare, evaluate)
        prepare.assert_not_called()
        evaluate.assert_not_called()
        self.assertFalse(self.output.exists())

    def test_target_stop_keeps_unevaluated_selection_charged(self):
        other = {'id': 'c' * 20, 'head': 'd' * 40}
        self.config['options'].update(history_limit=2, max_candidates=2)
        evaluate = Mock(return_value=self.candidate)
        result = run_batch(self.config, self.output,
                           self.prepare([self.candidate, other]), evaluate)
        evaluate.assert_called_once()
        self.assertEqual(result['attempted'], len([self.candidate, other]))
        self.assertEqual(result['selected_not_evaluated'], [other['id']])

    def test_mismatched_result_identity_is_not_a_success(self):
        with self.assertRaisesRegex(ValueError, 'different identity'):
            run_batch(self.config, self.output, self.prepare([self.candidate]),
                      Mock(return_value={'id': 'd' * 20}))
        result = json.loads((self.output / 'generation.json').read_text())
        self.assertEqual(result['candidates'], [])
        self.assertEqual(result['selected_not_evaluated'], [self.candidate['id']])

    def test_summary_preserves_charged_but_unevaluated_selection(self):
        self.output.mkdir()
        data = {'attempted': 2, 'candidates': [self.candidate], 'rejected': [],
                'selected_not_evaluated': ['c' * 20]}
        raw = json.dumps(data).encode()
        with tarfile.open(self.output / 'native-evidence.tar.gz', 'w:gz') as archive:
            member = tarfile.TarInfo('native/generation/generation.json')
            member.size = len(raw)
            archive.addfile(member, io.BytesIO(raw))
        result = summarize(self.output, self.output / 'summary.json')
        self.assertEqual(result['attempted'], 2)
        self.assertEqual(result['execution_passed'], 1)
        self.assertEqual(result['selected_not_evaluated'], ['c' * 20])

    def test_history_route_cannot_enable_flow_adaptation(self):
        self.assertEqual(recipe_arguments({'BIOTASKS21_RECIPE': 'r2e_gym'}),
                         ['--recipe', 'r2e_gym'])
        with self.assertRaises(ValueError):
            recipe_arguments({'BIOTASKS21_RECIPE': 'r2e_gym',
                              'BIOTASKS21_FLOW_TEST_PATHS': '1'})


if __name__ == '__main__':
    unittest.main()
