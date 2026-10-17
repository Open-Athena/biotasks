"""Inspect preserved DataArc text without executing generated code."""
import argparse
import ast
import hashlib
import json
from pathlib import Path


def audit(root):
    responses = []
    for path in sorted((root / 'raw').glob('*.json')):
        raw = json.loads(path.read_text())
        draft = json.loads(raw['content'])
        code = draft['tests_python']
        row = {'file': str(path.relative_to(root)), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
               'finish_reason': raw['finish_reason'], 'test_characters': len(code),
               'test_newlines': code.count('\n'), 'test_literal_backslash_n': code.count('\\n'),
               'declared_weight_names': [x['name'] for x in draft['weights']],
               'environment_files': [{'path': x['path'], 'newlines': x['content'].count('\n')}
                                     for x in draft['environment_files']]}
        try:
            tree = ast.parse(code)
            row.update(syntax_valid=True, top_level_nodes=[type(x).__name__ for x in tree.body],
                       top_level_tests=[x.name for x in tree.body
                                        if isinstance(x, (ast.FunctionDef, ast.AsyncFunctionDef))
                                        and x.name.startswith('test_')])
        except SyntaxError as exc:
            row.update(syntax_valid=False, syntax_error=exc.msg, syntax_error_line=exc.lineno)
        responses.append(row)
    feedback = []
    for path in sorted(root.glob('runs/*/candidates/*/builder-*.request.json')):
        request = json.loads(path.read_text())
        user = json.loads(request['user'])
        feedback.append({'file': str(path.relative_to(root)),
                         'materialization_errors': [x['materialization_error'] for x in user.get('feedback', [])
                                                    if 'materialization_error' in x]})
    return {'stage': 'offline_preserved_response_audit', 'responses': responses, 'repair_feedback': feedback,
            'generated_code_executed': False, 'new_model_calls': 0,
            'conclusion': 'First tests field contains imports but no tests; second is invalid Python. Environment file fields contain actual newlines. Neither saved response supplies a runnable verifier.',
            'limitations': ['No causal claim about model reasoning effort or token allocation.',
                            'Third dispatched request has no saved response.',
                            'No generated prose claiming test success is execution evidence.']}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.write_text(json.dumps(audit(args.root), indent=2) + '\n')
