"""Native prompt/schema parity fixtures; zero live inference or execution."""

import ast
import inspect
import json
import tempfile
import unittest
from importlib.resources import files
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from author_history_issue import write_issue, native, bounded_context


class HistoryAuthorTests(unittest.TestCase):
    def setUp(self):
        self.candidate = {'id': 'a' * 20, 'title': 'Synthetic fixture',
                          'contrast': {'FAIL_TO_PASS': ['synthetic_test']}}

    def test_pinned_native_prompt_context_schema_and_call_contract(self):
        tree = ast.parse(inspect.getsource(native))
        call = next(node for node in ast.walk(tree)
                    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                    and node.func.id == 'metered_complete')
        system = next(kw.value for kw in call.keywords if kw.arg == 'system')
        expected = eval(compile(ast.Expression(system), '<pinned-native-prompt>', 'eval'),
                        {'resources': files('repo2rlenv.pipelines.recipes.r2e_gym')})
        response = {'analysis': 'Synthetic analysis of a retained executable contrast.',
                    'instruction': 'Synthetic task statement for the fixture. ' * 4}
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(native, 'metered_complete', return_value=SimpleNamespace(
                    content=json.dumps(response))) as complete:
                issue = write_issue(self.candidate, 'r2e_gym', object(), object(), Path(directory))
        complete.assert_called_once()
        kwargs = complete.call_args.kwargs
        self.assertEqual(kwargs['system'], expected)
        self.assertEqual(kwargs['user'], bounded_context(self.candidate))
        self.assertEqual(kwargs['response_schema'], native.HistoricalIssue.model_json_schema())
        self.assertEqual(kwargs['max_tokens'], 5000)
        self.assertEqual(kwargs['reservation_usd'], '0.75')
        self.assertFalse(kwargs['resume'])
        self.assertEqual(issue.instruction, response['instruction'])

    def test_missing_contrast_is_rejected_before_inference(self):
        self.candidate['contrast']['FAIL_TO_PASS'] = []
        with patch.object(native, 'metered_complete') as complete:
            with self.assertRaisesRegex(ValueError, 'executable contrast'):
                write_issue(self.candidate, 'r2e_gym', object(), object(), Path('/unused'))
        complete.assert_not_called()

    def test_unrelated_recipe_is_rejected_before_inference(self):
        with patch.object(native, 'metered_complete') as complete:
            with self.assertRaisesRegex(ValueError, 'Unsupported'):
                write_issue(self.candidate, 'swe_flow', object(), object(), Path('/unused'))
        complete.assert_not_called()


if __name__ == '__main__':
    unittest.main()
