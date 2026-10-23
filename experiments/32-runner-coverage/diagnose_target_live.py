"""Summarize unchanged live evidence; do not repair or regrade it."""
import json
import re
from pathlib import Path

ROOT=Path(__file__).resolve().parent


def main():
    readback=json.loads((ROOT/'live-readback.json').read_text())
    assert readback['cleanup_verified']
    data=ROOT/'inputs-private/live-001/comparison'
    rows=[]
    for arm in readback['arms']:
        if arm['pr']!=958:continue
        for call in arm['stages']:
            text=(data/f"958-{arm['selection']}"/f"call-{call['index']:02d}-stdout.txt").read_text()
            missing='ERROR: file or directory not found:' in text
            chemap="ModuleNotFoundError: No module named 'chemap'" in text
            collection=re.search(r'collected (\d+) items(?: / (\d+) errors)?',text)
            assert collection
            if arm['selection']=='original-targets':assert missing and not chemap
            else:assert chemap and not missing
            rows.append({'selection':arm['selection'],'stage':call['stage'],
                         'missing_target_error':missing,'missing_chemap_error':chemap,
                         'collected_items':int(collection[1]),'collection_errors':int(collection[2] or 0),
                         'outer_exit_code':call['exit_code'],'stdout_sha256':call['stdout_sha256'],
                         'native_status':arm['status'],'f2p_count':arm['f2p_count']})
    a,b=[json.loads((data/f'671-{selection}/outcome-private.json').read_text())
         for selection in ('original-targets','surviving-targets')]
    assert a['fail_to_pass']==b['fail_to_pass'] and a['pass_to_pass']==b['pass_to_pass']
    result={'scope':'General deleted-target selection on frozen inputs; native validation only',
            'rows':rows,'control_exact_sets_equal':True,'control_f2p_count':len(a['fail_to_pass']),
            'control_p2p_count':len(a['pass_to_pass']),'recovered_tasks':0,'model_calls':0,
            'allocated_cpu_hours':readback['allocated_cpu_hours'],'cleanup_verified':True,
            'limits':['No dependency repair; missing chemap remains a separate environment blocker',
                      'Collected items are not executed passing tests; collection interrupted both candidate stages',
                      'No SGR/completion/rebuild change applied','No new exports or independent Harbor controls',
                      'Same reconstructed image for all arms; original deleted image not reproduced byte-for-byte']}
    (ROOT/'target-live-diagnosis.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result))


if __name__=='__main__':main()
