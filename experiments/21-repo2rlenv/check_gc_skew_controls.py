"""Check target-only edits and synthetic independent GC-skew examples."""
import ast
from types import SimpleNamespace
from prepare_alpha_mutation_controls import replace_body
from prepare_gc_skew_controls import CASES
source = '''def GC_skew(seq, window=100):
    """Preserve this contract."""
    ...

def unrelated(x):
    return x + 1
'''
for name, (body, reward) in CASES.items():
    changed = replace_body(source, 'GC_skew', body)
    before, after = ast.parse(source), ast.parse(changed)
    assert ast.dump(before.body[1]) == ast.dump(after.body[1])
    assert ast.get_docstring(before.body[0]) == ast.get_docstring(after.body[0])
    namespace = {}
    exec(compile(changed, '<synthetic fixture>', 'exec'), namespace)
    function = namespace['GC_skew']
    if name == 'alternative_character_loop':
        assert reward == 1
        assert function('GCcAg', 2) == [0.0, -1.0, 1.0]
        assert function(SimpleNamespace(seq='GCcAg'), 2) == [0.0, -1.0, 1.0]
        assert function('AaNn') == [0.0]
        assert function('') == []
    else:
        assert reward is None
        assert function('GCcAg', 2) != [0.0, -1.0, 1.0]
print('PASS: isolated edit, preserved contract, independent synthetic examples and coverage diagnostics')
