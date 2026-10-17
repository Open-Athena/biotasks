"""Independent semantic checks for recovered SCALER exports; no generated code execution.

This does not establish runtime isolation or complete task acceptance.
"""
import argparse
import ast
import hashlib
import heapq
import json
from pathlib import Path
import tomllib


def shortest_path(first, second):
    queue=[(0,0,0)];visited=set()
    while queue:
        cost,i,j=heapq.heappop(queue)
        if (i,j) in visited:continue
        visited.add((i,j))
        if i==len(first) and j==len(second):return cost
        if i<len(first):heapq.heappush(queue,(cost+1,i+1,j))
        if j<len(second):heapq.heappush(queue,(cost+1,i,j+1))
        if i<len(first) and j<len(second):heapq.heappush(queue,(cost+(first[i]!=second[j]),i+1,j+1))
    raise AssertionError('No path')


def audit(campaign, family):
    digest=hashlib.sha256(family.read_bytes()).hexdigest();rows=[]
    for task in sorted((campaign/'tasks').iterdir()):
        config=tomllib.loads((task/'task.toml').read_text())
        metadata=config['metadata']['repo2env']
        assert metadata['source_sha256']==digest
        assert metadata['answer_contract']=={'output_type':'number'}
        assert (metadata['reward_min'],metadata['reward_max'])==(-1,1)
        key=task.name.removeprefix('scaler-')
        instance=json.loads((campaign/'runs/scaler-dna-01/scaler-dna-01/candidates'/key/'instance.json').read_text())
        instruction=(task/'instruction.md').read_text()
        assert instruction.strip()==instance['instruction'].strip()
        concrete=ast.literal_eval(instruction.split('# Input Instance:\n',1)[1].split('\n\n# Instruction',1)[0])
        assert set(concrete)=={'first','second'}
        first,second=concrete['first'],concrete['second']
        assert isinstance(first,str) and isinstance(second,str) and max(len(first),len(second))<=20
        assert set(first+second)<=set('ACGT')
        expected=shortest_path(first,second)
        reference=json.loads((task/'tests/reference.json').read_text())
        answer='\\boxed{'+str(expected)+'}'
        assert reference==instance['reference_answer']==answer
        assert (task/'solution/answer.txt').read_text().strip()==answer
        assert config['verifier']['environment_mode']=='separate'
        assert config['agent']['user']=='learner'
        assert config['artifacts']==[{'source':'/workspace/answer.txt'}]
        assert sorted(p.relative_to(task/'environment').as_posix() for p in (task/'environment').rglob('*') if p.is_file())==['Dockerfile']
        dockerfile=(task/'environment/Dockerfile').read_text()
        assert not any(line.split(maxsplit=1)[0].upper() in {'COPY','ADD'} for line in dockerfile.splitlines() if line.strip())
        rows.append({'task_id':task.name,'bundle_hash':metadata['bundle_hash'],'lengths':[len(first),len(second)],
                     'independent_minimum_edit_cost':expected,'reference_agrees':True,
                     'source_sha256':digest,'static_verifier_separation':True})
    assert len(rows)==3
    return {'stage':'independent_offline_semantic_audit','tasks':rows,
            'method':'Shortest paths over insertion/deletion/substitution transitions; generated reference programs were not executed.',
            'independently_accepted_tasks':0,'remaining':['runtime verifier controls for alternative and incorrect answers','runtime private-path checks','Marin conversion and parity','blind solver on accepted tasks'],
            'competency':'Exact string edit-distance computation on synthetic DNA-alphabet strings; general algorithmic reasoning with biological notation.',
            'split_group':'scaler-dna-edit-v1','independent_family_count':1}


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    for name in ('campaign','family','output'):parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args();result=audit(args.campaign,args.family)
    args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result))
