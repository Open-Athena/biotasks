"""Prepare independent alpha-diversity submissions with unchanged native assets."""
import argparse
import ast
import json
import shutil
from pathlib import Path

SOURCE = 'skbio/diversity/alpha/_base.py'
CASES = {
    'strong': {
        'alternative_cumulative': ('''total = float(counts.sum())
ordered = sorted(counts, reverse=True)
cumulative = 0.0
result = 0.0
for index, count in enumerate(ordered, 1):
    cumulative += count
    result = max(result, cumulative / total - index / len(ordered))
return np.float64(result)''', 1),
        'wrong_fixed_example': ('return np.float64(3 / 14)', None),
        'wrong_zero': ('return np.float64(0)', 0),
    },
    'esty_ci': {
        'alternative_factored_variance': ('''total = float(counts.sum())
singletons = float(np.count_nonzero(counts == 1))
doubletons = float(np.count_nonzero(counts == 2))
center = singletons / total
variance = (singletons * (1 - center) + 2 * doubletons) / (total * total)
width = 1.959963985 * np.sqrt(variance)
return center - width, center + width''', 1),
        'wrong_clipped_lower': ('''N = counts.sum()
f1 = (counts == 1).sum()
f2 = (counts == 2).sum()
width = 1.959963985 * np.sqrt((f1 * (N - f1) + 2 * N * f2) / N**3)
return max(0.0, f1 / N - width), f1 / N + width''', 0),
        'wrong_omit_doubletons': ('''N = counts.sum()
f1 = (counts == 1).sum()
width = 1.959963985 * np.sqrt(f1 * (N - f1) / N**3)
return f1 / N - width, f1 / N + width''', 0),
    },
}


def replace_body(source, function, body):
    matches = [n for n in ast.parse(source).body
               if isinstance(n, ast.FunctionDef) and n.name == function]
    if len(matches) != 1:
        raise ValueError('Expected exactly one target function')
    node = matches[0]
    statements = node.body
    if isinstance(statements[0], ast.Expr) and isinstance(statements[0].value, ast.Constant) and isinstance(statements[0].value.value, str):
        statements = statements[1:]
    if not statements:
        raise ValueError('Missing implementation')
    lines = source.splitlines(keepends=True)
    indent = ' ' * statements[0].col_offset
    lines[statements[0].lineno - 1:node.end_lineno] = [indent + line + '\n' for line in body.splitlines()]
    result = ''.join(lines)
    ast.parse(result)
    return result


def prepare(task, output, function):
    from repo2rlenv.emitter.bundle import inspect_bundle
    from prepare_skbio_pr_controls import retained_hashes
    identity = inspect_bundle(task)
    if not identity['integrity_passed']:
        raise ValueError('Original native bundle changed')
    config = json.loads((task/'tests/contract.json').read_text())
    if config['submitted_files'] != [SOURCE] or len(config['expected_passes']) != 34:
        raise ValueError('Unexpected native contract')
    source = (task/'environment/source'/SOURCE).read_text()
    output.mkdir(parents=True, exist_ok=False)
    assets = retained_hashes(task)
    records = []
    cases = [('baseline', None, 0), ('native_reference', None, 1)]
    cases += [(name, body, reward) for name, (body, reward) in CASES[function].items()]
    for name, body, reward in cases:
        destination = output/name
        shutil.copytree(task, destination)
        if name == 'baseline':
            script = '#!/bin/sh\nset -eu\n# Leave the original defective source unchanged.\n'
        elif body is not None:
            changed = replace_body(source, function, body)
            program = "from pathlib import Path\nPath('/workspace/" + SOURCE + "').write_text(" + repr(changed) + ")\n"
            script = "#!/bin/sh\nset -eu\npython3 - <<'PYCONTROL'\n" + program + 'PYCONTROL\n'
        else:
            script = (task/'solution/solve.sh').read_text()
        (destination/'solution/solve.sh').write_text(script)
        assert retained_hashes(destination) == assets
        records.append({'case':name,'bundle':str(destination),'expected_reward':reward,
                        'interpretation':'coverage diagnostic; no pass/fail expectation' if reward is None else 'independent correctness control'})
    manifest = {'stage':'prepared_unexecuted','function':function,
                'source_bundle_hash':identity['bundle_hash'],'unchanged_assets':assets,
                'cases':records,'limits':['Original source, grader and contract preserved','No control execution or acceptance claimed']}
    (output/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    return manifest


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--task',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--function',choices=tuple(CASES),required=True)
    args = parser.parse_args()
    prepare(args.task,args.output,args.function)
