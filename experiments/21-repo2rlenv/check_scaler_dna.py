"""Check native family parsing and references against independent shortest paths."""
import heapq
import itertools
import json
import random
from pathlib import Path
from repo2rlenv.pipelines.recipes.scaler.families import load_families, scale_parameters, parse_testcase, instruction_for
from repo2rlenv.pipelines.recipes.scaler.compatibility import fix_newlines_in_python_strings, import_needed_module_for_python
from repo2rlenv.spec.recipe_options import ScalerOptions


def shortest_path(first, second):
    queue=[(0,0,0)];visited=set()
    while queue:
        cost,i,j=heapq.heappop(queue)
        if (i,j) in visited:continue
        visited.add((i,j))
        if i==len(first) and j==len(second):return cost
        if i<len(first):heapq.heappush(queue,(cost+1,i+1,j))
        if j<len(second):heapq.heappush(queue,(cost+1,i,j+1))
        if i<len(first) and j<len(second):
            heapq.heappush(queue,(cost+(first[i]!=second[j]),i+1,j+1))


root=Path(__file__).resolve().parent
profile=json.loads((root/'scaler-dna-profile.json').read_text())
families,digest=load_families(root/profile['source']['path'])
assert digest==profile['source_sha256']
options=ScalerOptions.model_validate(profile['options'])
family=families['synthetic_dna_edit_distance']
reference={'__name__':'reference_fixture'}
exec(compile(family['solutions']['solution'][0],'<reference>','exec'),reference)
generator={}
code=fix_newlines_in_python_strings(import_needed_module_for_python(family['generate_testcase']))
exec(compile(code,'<native-compatible-generator>','exec'),generator)
values=[''.join(x) for n in range(4) for x in itertools.product('AC',repeat=n)]
for first,second in itertools.product(values,repeat=2):
    assert reference['distance'](first,second)==shortest_path(first,second)
seen=set()
for difficulty in options.difficulties:
    for seed in range(6):
        random.seed(seed)
        stdin,detail=parse_testcase(str(generator['generate_testcase'](scale_parameters(family,difficulty))))
        assert stdin.splitlines()==[detail['first'],detail['second']]
        assert len(detail['first'])==len(detail['second'])==difficulty+4
        assert set(detail['first']+detail['second'])<=set('ACGT')
        assert reference['distance'](detail['first'],detail['second'])==shortest_path(detail['first'],detail['second'])
        assert '/workspace/answer.txt' in instruction_for(family,detail)
        seen.add(stdin)
assert len(seen)==36
print(json.dumps({'passed':True,'exhaustive_short_pairs':len(values)**2,'generated_instances':36,'native_family_parser':True,'native_compatibility_transform':True,'native_options':options.model_dump(mode='json'),'model_calls':0,'remote_execution':False}))
