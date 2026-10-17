"""Synthetic checks that control edits preserve decorators and unrelated code."""
import ast
from prepare_alpha_mutation_controls import replace_body, CASES

source = '''@decorate(empty=float('nan'))
def strong(counts):
    """Preserved contract."""
    value = 1
    return value

def unrelated(x):
    return x + 1
'''
changed = replace_body(source, 'strong', CASES['strong']['alternative_cumulative'][0])
before, after = ast.parse(source), ast.parse(changed)
assert ast.dump(before.body[1]) == ast.dump(after.body[1])
assert ast.dump(before.body[0].decorator_list[0]) == ast.dump(after.body[0].decorator_list[0])
assert ast.get_docstring(before.body[0]) == ast.get_docstring(after.body[0])
assert 'return value' not in changed
for invalid in ('def other(x):\n    return x\n', source + '\ndef strong(x):\n    return x\n'):
    try: replace_body(invalid, 'strong', 'return 0')
    except ValueError: pass
    else: raise AssertionError('Ambiguous target accepted')
for function, cases in CASES.items():
    fixture = source.replace('strong', function)
    for body, _ in cases.values(): ast.parse(replace_body(fixture, function, body))
assert CASES['strong']['wrong_fixed_example'][1] is None
print('PASS: target-only replacement, decorators/docstrings retained, ambiguous targets rejected, diagnostic has no forced reward')
