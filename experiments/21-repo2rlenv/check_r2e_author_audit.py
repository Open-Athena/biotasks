"""Reject misleading audit totals and preserve code without executing it."""
import json
import tempfile
from pathlib import Path
from audit_r2e_authoring import audit

with tempfile.TemporaryDirectory() as temporary:
    root=Path(temporary);(root/'raw').mkdir()
    (root/'controller-result.json').write_text(json.dumps({'status':'completed','cleanup':'still_present','result':{'candidates':4,'emitted':0}}))
    contents=[json.dumps({'test_code':"raise RuntimeError('must not execute')\ndef test_example():\n    assert True\n"}),
              json.dumps({'test_code':'# comment only'}),
              '{"test_code":"invalid\nJSON control character"}',
              json.dumps({'test_code':'def ??:'})]
    for index,content in enumerate(contents,1):
        raw={'content':content,'finish_reason':'stop'}
        if index==1:raw['usage']={'prompt_tokens':4,'completion_tokens':6,'total_tokens':10,'completion_tokens_details':{'reasoning_tokens':2}}
        (root/'raw'/f'call-{index:03}.json').write_text(json.dumps(raw))
    result=audit(root)
    assert result['model_responses']==4
    assert result['structured_content_failures']==1 and result['syntax_failures']==1
    assert result['parseable_empty_modules']==1
    assert result['records'][0]['test_definitions']==1
    assert result['records'][0]['test_code_newlines']==3
    assert all(value is None for value in result['usage'].values())
    assert '1 Python syntax failures' in result['interpretation']
print('PASS: malformed content retained, code unexecuted, actual newline/test definitions counted, missing usage remains unknown, interpretation uses observed counts')
