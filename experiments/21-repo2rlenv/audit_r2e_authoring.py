"""Summarize preserved R2E author responses without executing generated code."""
import argparse
import ast
from collections import Counter
import hashlib
import json
from pathlib import Path


def audit(campaign):
    controller = json.loads((campaign/'controller-result.json').read_text())
    records = []
    usages = []
    reasons = Counter()
    for path in sorted((campaign/'raw').glob('call-*.json')):
        assert path.stat().st_size <= 4*1024**2
        data = path.read_bytes()
        raw = json.loads(data)
        code = None
        parse_error = None
        try:
            content = json.loads(raw['content'])
            code = content['test_code']
            if not isinstance(code, str):
                raise TypeError('test_code must be a string')
        except (json.JSONDecodeError, KeyError, TypeError) as error:
            code = None
            parse_error = type(error).__name__
        statements = None
        test_definitions = None
        syntax = 'unavailable'
        if code is not None:
            try:
                tree = ast.parse(code)
                statements = len(tree.body)
                test_definitions = sum(isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith('test') for node in ast.walk(tree))
                syntax = 'valid'
            except SyntaxError as error:
                syntax = f'{error.msg} (line {error.lineno})'
        usages.append(raw.get('usage') or {})
        reasons[raw.get('finish_reason', 'unknown')] += 1
        records.append({
            'file': path.name, 'sha256': hashlib.sha256(data).hexdigest(),
            'content_parse_error': parse_error,
            'test_code_characters': len(code) if code is not None else None,
            'test_code_newlines': code.count('\n') if code is not None else None,
            'literal_backslash_n': code.count('\\n') if code is not None else None,
            'html_breaks': code.count('<br>') if code is not None else None,
            'syntax': syntax, 'top_level_statements': statements, 'test_definitions': test_definitions,
            'requested_max_tokens': raw.get('requested_max_tokens'),
            'requested_reasoning_effort': raw.get('requested_reasoning_effort'),
        })
    usage = {
        key: sum(item[key] for item in usages)
        if usages and all(type(item.get(key)) is int for item in usages) else None
        for key in ('prompt_tokens', 'completion_tokens', 'total_tokens')
    }
    reasoning = [(item.get('completion_tokens_details') or {}).get('reasoning_tokens')
                 for item in usages]
    usage['reasoning_tokens'] = (sum(reasoning) if reasoning and
                                all(type(value) is int for value in reasoning) else None)
    invalid = sum(r['syntax'] not in ('valid', 'unavailable') for r in records)
    empty = sum(r['top_level_statements'] == 0 for r in records)
    malformed = sum(r['content_parse_error'] is not None for r in records)
    interpretation = (
        f"Native result: {controller['result']['candidates']} candidates, "
        f"{controller['result']['emitted']} exports. Preserved responses include "
        f"{malformed} structured-content failures, {invalid} Python syntax failures "
        f"and {empty} empty modules. Missing usage stays unknown. Formatting origin "
        "is not established; do not silently rewrite responses or attribute failures to biology."
    )
    return {
        'stage': 'recovered_authoring_audit', 'controller_status': controller['status'],
        'candidate_result': controller['result'],
        'controller_cleanup_observation': controller['cleanup'],
        'model_responses': len(records), 'finish_reasons': dict(reasons), 'usage': usage,
        'structured_content_failures': malformed, 'syntax_failures': invalid,
        'parseable_empty_modules': empty,
        'parseable_without_explicit_test_definitions': sum(r['test_definitions'] == 0 for r in records),
        'responses_with_no_code_newlines': sum(r['test_code_newlines'] == 0 for r in records),
        'records': records, 'independently_accepted_tasks': 0, 'blind_solver_attempts': 0,
        'interpretation': interpretation,
    }


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--campaign', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.campaign)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps({k: v for k, v in result.items() if k != 'records'}))
