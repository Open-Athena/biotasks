"""Reconcile preserved native/Marin evidence by reward and environment structure."""
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parent


def build():
    sources={}
    def read(name):
        raw=(ROOT/name).read_bytes();sources[name]=hashlib.sha256(raw).hexdigest()
        return json.loads(raw)
    pr=read('evidence/marin-pr-runtime-02/controls.json')
    lcc=read('evidence/marin-lcc-runtime-02/runtime-result.json')['cases']
    scaler=read('evidence/marin-scaler-runtime-01/runtime-result.json')['tasks']
    diagnosis=read('evidence/marin-scaler-runtime-01/score-range-diagnosis.json')
    def pairs(cases):
        result=[]
        for row in cases:
            assert row['native_reward']==row['marin_reward']
            if 'expected_reward' in row:assert row['native_reward']==row['expected_reward']
            assert row['marin_result']['status']=='graded' and row['marin_result']['error'] is None
            result.append({'case':row['case'],'native_reward':row['native_reward'],'marin_reward':row['marin_reward']})
        return result
    pr_pairs=pairs(pr);lcc_pairs=pairs(lcc)
    numeric=[]
    for task in scaler:
        numeric.append({'task_id':task['task_id'],'cases':pairs(task['cases']),
                        'range_metadata_matches':task['score_range_metadata_matches']})
    diff_controls=read('evidence/marin-runtime-02/native/runtime/controls.json')
    diff_controller=read('evidence/marin-runtime-02/controller-result.json')
    assert diff_controller['status']=='worker_completed' and diff_controller['worker_returncode']==0
    diff_pairs=pairs(diff_controls)
    lcc_summary=read('evidence/lcc-marin-preparation/conversion-summary.json')
    return {'stage':'evidence_reconciliation_not_new_execution',
            'marin_revision':diagnosis['marin_revision'],'atlas_admission_established':False,
            'structures':[
                {'name':'PR-diff workspace/Git patch similarity','representative':'scikit-bio PR2630',
                 'status':'representative_runtime_parity_passed','cases':diff_pairs,
                 'limitation':'Three controls match after the ConversationTrace harness correction. Similarity is not functional correctness; the ephemeral local registry image is not a public training image.'},
                {'name':'Portable repository test grader with fractional F2P/P2P reward','representative':'scikit-bio PR2633 portable profile',
                 'status':'representative_runtime_parity_passed','cases':pr_pairs,
                 'limitation':'Applies to this explicit compiled-runtime adaptation; does not validate every repository or native history export.'},
                {'name':'Separate learner/verifier source contexts with allowed-source collection and binary pytest reward',
                 'representative':'Biopython LCC','status':'representative_runtime_parity_passed','cases':lcc_pairs,
                 'grader_sha256':lcc_summary['key_asset_hashes']['tests/grade.py'],
                 'wrapper_sha256':lcc_summary['key_asset_hashes']['tests/test.sh'],
                 'limitation':'Representative structure covered. Different source images, fixtures, allowed files and candidate contracts still require task-specific validation.'},
                {'name':'Separate numeric-answer verifier with native -1/+1 reward','representative':'SCALER synthetic edit-distance family',
                 'status':'raw_reward_parity_but_metadata_incompatible','tasks':numeric,
                 'limitation':diagnosis['conclusion']}],
            'source_sha256':sources,'next_required':[
                'PR-diff representative reward parity is established; task acceptance and public image availability remain separate checks.',
                'Retain the SCALER score-range metadata incompatibility; do not normalize native rewards silently.',
                'Inspect any new export for genuinely different verifier/environment structures.',
                'Complete task-specific acceptance and solver work independently of representative conversion evidence.']}


if __name__=='__main__':
    result=build();out=ROOT/'evidence/marin-structure-coverage';out.mkdir(exist_ok=True)
    (out/'coverage.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'structures':len(result['structures']),'source_records':len(result['source_sha256']),
                      'pr_cases':len(result['structures'][1]['cases']),'lcc_cases':len(result['structures'][2]['cases']),
                      'numeric_cases':sum(len(x['cases']) for x in result['structures'][3]['tasks'])}))
