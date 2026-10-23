"""Summarize verified frozen MACS validation evidence, without altering tasks."""
import hashlib
import json
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parent
RAW=ROOT/'inputs-private/macs-native-001'

def sha(path):
    with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()

def main():
    receipt=json.loads((ROOT/'macs-native-readback-001.json').read_text())
    assert receipt['record_verified'] and receipt['owned_containers_absent'] and receipt['tools_removed'] and not receipt['cleanup_errors']
    assert [a['name'] for a in receipt['arms']]==['original','rebuild']
    assert all(a['state']=='completed' and a['native_outcome_record'] for a in receipt['arms'])
    source=(ROOT/'inputs-private/macs-native-792/source.patch').read_text()
    tests=(ROOT/'inputs-private/macs-native-792/test.patch').read_text()
    assert 'diff --git a/MACS3/Signal/CallerExecution.py b/MACS3/Signal/CallerExecution.py\nnew file mode 100644' in source
    assert '+import MACS3.Signal.CallerExecution as execution' in tests
    arms=[]
    for name in ['original','rebuild']:
        outcome=json.loads((RAW/name/'outcome.json').read_text())
        calls=json.loads((RAW/name/'calls.json').read_text())
        assert outcome['status']=='failed' and outcome['reason']=='no fail-to-pass tests after validation'
        assert not outcome['fail_to_pass'] and not outcome['pass_to_pass']
        assert [c['stage'] for c in calls if c['stage']]==['pre','post']
        stages=[]
        for stage,index in [('pre',3),('post',4)]:
            call=calls[index];assert call['stage']==stage and call['timeout']==600 and call['exit_code']==0
            path=RAW/name/f'call-{index:02d}-stdout.txt';text=path.read_text()
            assert sha(path)==call['stdout_sha256']
            errors=len(re.findall(r'^_{4,} ERROR collecting ',text,re.M))
            summaries=re.findall(r'^=+\s*(\d+) passed, (\d+) skipped in ([0-9.]+)s.*=+$',text,re.M)
            assert len(summaries)<=1
            stages.append({'stage':stage,'command_sha256':call['command_sha256'],'outer_exit_code':call['exit_code'],
                           'duration_seconds':call['duration_sec'],'collection_errors':errors,
                           'stale_extension_spec_error': 'AttributeError: __spec__' in text,
                           'missing_new_pr_module':"No module named 'MACS3.Signal.CallerExecution'" in text,
                           'pytest_summary':{'passed':int(summaries[0][0]),'skipped':int(summaries[0][1]),'seconds':float(summaries[0][2])} if summaries else None})
        arms.append({'name':name,'validator_status':outcome['status'],'reason':outcome['reason'],
                     'fail_to_pass_count':0,'pass_to_pass_count':0,'stages':stages})
    assert [s['collection_errors'] for s in arms[0]['stages']]==[3,3]
    assert [s['stale_extension_spec_error'] for s in arms[0]['stages']]==[True,True]
    assert arms[1]['stages'][0]['collection_errors']==1 and arms[1]['stages'][0]['missing_new_pr_module']
    assert arms[1]['stages'][1]['collection_errors']==0 and arms[1]['stages'][1]['pytest_summary']['passed']==364
    result={'scope':'Verified PR792 native original-versus-rebuild comparison; no task repair or regrading',
            'archive_sha256':receipt['archive_sha256'],'source_patch_sha256':sha(ROOT/'inputs-private/macs-native-792/source.patch'),
            'test_patch_sha256':sha(ROOT/'inputs-private/macs-native-792/test.patch'),
            'new_module_in_source_patch':True,'new_module_imported_by_test_patch':True,'arms':arms,
            'positive_f2p_pair':False,'exported_controls_run':0,'model_calls':0,'allocated_cpu_hours':receipt['allocated_cpu_hours'],
            'conclusion':'Rebuild improves patched-stage collection, but the frozen test patch cannot collect at base because it imports a module first introduced by this PR; no fail-to-pass result.',
            'limits':['Outer stage exit0 masks pytest collection failure because upstream stage script echoes a final marker','Post stage pass does not establish base-to-patch fail-to-pass behavior','Mutable reconstructed dependencies can differ from deleted original image','No exported task or independent nop/oracle controls']}
    (ROOT/'macs-native-diagnosis.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ('arms','limits')}))
if __name__=='__main__':main()
