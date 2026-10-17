"""Summarize preserved R2E author responses without executing generated code."""
import argparse
import ast
from collections import Counter
import hashlib
import json
from pathlib import Path


def audit(campaign):
    controller=json.loads((campaign/'controller-result.json').read_text())
    records=[];usage=Counter();reasons=Counter()
    for path in sorted((campaign/'raw').glob('call-*.json')):
        assert path.stat().st_size<=4*1024**2
        raw=json.loads(path.read_text());content=json.loads(raw['content']);code=content['test_code']
        statements=None
        try:
            statements=len(ast.parse(code).body);syntax='valid'
        except SyntaxError as error:
            syntax=f'{error.msg} (line {error.lineno})'
        for key in ('prompt_tokens','completion_tokens','total_tokens'):
            usage[key]+=(raw.get('usage') or {}).get(key,0) or 0
        reasons[raw['finish_reason']]+=1
        records.append({'file':path.name,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
            'test_code_characters':len(code),'test_code_newlines':code.count('\n'),
            'literal_backslash_n':code.count('\\n'),'html_breaks':code.count('<br>'),
            'syntax':syntax,'top_level_statements':statements,'requested_max_tokens':raw['requested_max_tokens'],
            'requested_reasoning_effort':raw['requested_reasoning_effort']})
    return {'stage':'recovered_authoring_audit','controller_status':controller['status'],
        'candidate_result':controller['result'],'controller_cleanup_observation':controller['cleanup'],
        'model_responses':len(records),'finish_reasons':dict(reasons),'usage':dict(usage),
        'syntax_failures':sum(r['syntax']!='valid' for r in records),
        'parseable_empty_modules':sum(r['top_level_statements']==0 for r in records),
        'responses_with_no_code_newlines':sum(r['test_code_newlines']==0 for r in records),
        'records':records,'independently_accepted_tasks':0,'blind_solver_attempts':0,
        'interpretation':'All candidate materialization attempts exhausted native repairs. All preserved code strings lack actual newlines; 26 fail Python parsing and four parse as empty comment-only modules. Root cause is not established; do not attribute this to biology or silently rewrite responses.'}


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--campaign',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();result=audit(args.campaign)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='records'}))
