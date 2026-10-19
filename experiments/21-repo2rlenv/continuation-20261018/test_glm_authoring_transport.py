"""Approved generation profile and unchanged solver profile, with zero live calls."""

import json
import ast
import unittest
from pathlib import Path

from run_glm_authoring_client import validate_author_request, transport_check
from run_glm_inference_client import validate_solver_request


class AuthoringTransportTests(unittest.TestCase):
    def body(self, **changes):
        payload = {'model': 'glm-5.3', 'max_tokens': 131072,
                   'messages': [{'role': 'user', 'content': 'Synthetic fixture'}],
                   'chat_template_kwargs': {'reasoning_effort': 'medium'}}
        payload.update(changes)
        return json.dumps(payload).encode()

    def test_generation_payload_and_effort_are_preserved(self):
        raw = self.body(response_format={'type': 'json_object'},
                        tools=[{'type': 'function', 'function': {
                            'name': 'synthetic_fixture',
                            'parameters': {'type': 'object', 'properties': {}}}}],
                        tool_choice='auto')
        self.assertEqual(validate_author_request(raw), json.loads(raw))
        self.assertEqual(transport_check(raw)['model_calls'], 0)

    def test_frozen_remote_probe_uses_approved_generation_payload(self):
        source = Path(__file__).with_name('run_glm_generation_transport_probe.py')
        tree = ast.parse(source.read_text())
        value = next(node.value for node in ast.walk(tree)
                     if isinstance(node, ast.Assign) and any(
                         isinstance(target, ast.Name) and target.id == 'payload'
                         for target in node.targets))
        payload = eval(compile(ast.Expression(value), '<owned-probe-payload>', 'eval'),
                       {'__builtins__': {}})
        self.assertEqual(payload['max_tokens'], 131072)
        self.assertEqual(validate_author_request(json.dumps(payload).encode()), payload)

    def test_both_output_limit_fields_must_fit_approved_ceiling(self):
        for bad in [131073, 0, -1, True, '131072']:
            with self.subTest(value=bad), self.assertRaises(ValueError):
                validate_author_request(self.body(max_completion_tokens=bad))

    def test_missing_or_conflicting_effort_cannot_silently_change_profile(self):
        for options in [{}, {'reasoning_effort': 'high'}]:
            with self.subTest(options=options), self.assertRaises(ValueError):
                validate_author_request(self.body(chat_template_kwargs=options))
        with self.assertRaises(ValueError):
            validate_author_request(self.body(reasoning_effort='high'))

    def test_solver_still_rejects_large_generation_allowance(self):
        with self.assertRaises(ValueError):
            validate_solver_request(self.body())
        payload = validate_solver_request(self.body(max_tokens=2048, chat_template_kwargs={}))
        self.assertEqual(payload['max_tokens'], 2048)

    def test_other_model_or_streaming_is_rejected_without_forwarding(self):
        for options in [{'model': 'other-model'}, {'stream': True}]:
            with self.subTest(options=options), self.assertRaises(ValueError):
                validate_author_request(self.body(**options))


if __name__ == '__main__':
    unittest.main()
