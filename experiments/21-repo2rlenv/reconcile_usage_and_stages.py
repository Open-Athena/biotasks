"""Reconcile retained model traffic and early stages without inventing missing calls."""
import datetime
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parent


def build():
    sources={}
    def read(name):
        raw=(ROOT/name).read_bytes();assert len(raw)<=16*1024**2
        sources[name]=hashlib.sha256(raw).hexdigest();return json.loads(raw)
    def total(items,key):
        values=[x.get(key) for x in items]
        return sum(values) if values and all(isinstance(x,int) for x in values) else None
    def usage(items):
        normalized=[]
        for item in items:
            normalized.append({'prompt_tokens':item.get('prompt_tokens'),'completion_tokens':item.get('completion_tokens'),
                               'reasoning_tokens':(item.get('completion_tokens_details') or {}).get('reasoning_tokens',item.get('reasoning_tokens'))})
        return {'input_tokens':total(normalized,'prompt_tokens'),'combined_output_tokens':total(normalized,'completion_tokens'),'reasoning_tokens':total(normalized,'reasoning_tokens')}
    subset=read('evidence/interim-results-20261017/reconciled-subset.json');rows=[]
    for item in subset['generation_rows']:
        count=item.get('preserved_model_responses')
        if count is None and item.get('model_calls',item.get('authoring_calls'))==0:count=0
        rows.append({'event':item['run'],'stage':'generation_materialization_or_authoring','preserved_response_count':count,
                     **{k:item.get(k) for k in ('input_tokens','combined_output_tokens','reasoning_tokens')},'source':item['source']})
    baseline_path='evidence/skbio-author-01/summary.json';baseline=read(baseline_path)
    rows.append({'event':'skbio-author-01-native4096','stage':'native_authoring_limit_baseline','candidate_count':3,'requests_reported':baseline['requests'],'preserved_response_count':len(baseline['calls']),'schema_valid_authored':baseline['authored'],
                 'input_tokens':baseline['prompt_tokens'],'combined_output_tokens':baseline['completion_tokens'],'reasoning_tokens':baseline['reasoning_tokens'],'source':baseline_path,
                 'limit':'4096 combined output tokens; native maximum two authoring attempts per saved candidate. Same candidate identities reused by explicitly adapted later stages, not new candidate discovery.'})
    seed_rows=[]
    for name in ('seta-design-01','parent-evolution-design-01'):
        path='evidence/'+name+'/summary.json';d=read(path)
        calls=d['calls'] if 'calls' in d else [x['usage'] for x in d['usage']]
        record={'event':name,'stage':'seed_or_parent_design','preserved_response_count':len(calls),**usage(calls),'source':path,'built_tasks_in_design_stage':d['built_tasks']}
        rows.append(record);seed_rows.append(record)
    calibration=[]
    for name,path in [('glm-preflight-01','evidence/glm-preflight/attempt-01.json'),('glm-preflight-02','evidence/glm-preflight/attempt-02.json'),
                      ('glm-author-budget-01','evidence/glm-author-budget-01/summary.json'),('glm-author-budget-02','evidence/glm-author-budget-02/result.json'),('glm-author-budget-03','evidence/glm-author-budget-03/glm-report.json')]:
        d=read(path);dispatched=d.get('model_calls_dispatched',d.get('model_calls'))
        missing=d.get('result')=='unavailable';captured=0 if missing or dispatched==0 else dispatched
        row={'event':name,'stage':d['stage'] if 'stage' in d else 'setup_before_model_dispatch','requests_reported':dispatched,'preserved_response_count':captured,
             'input_tokens':d.get('prompt_tokens',0 if dispatched==0 else None),'combined_output_tokens':d.get('completion_tokens',0 if dispatched==0 else None),'reasoning_tokens':d.get('reasoning_tokens',0 if dispatched==0 else None),
             'max_output_tokens':d.get('max_output_tokens'),'requested_effort':d.get('reasoning_effort'),'source':path,'response_unavailable':missing}
        rows.append(row);calibration.append(row)
    solver_rows=[]
    for item in subset['solver_rows']:
        source=read(item['source']);episodes=source.get('turns',source.get('agent_episodes',source.get('episodes')))
        row={'event':item['run'],'stage':'blind_solver','attempts':item['attempts'],'agent_episodes':episodes,'preserved_response_count':episodes,
             'input_tokens':item.get('input_tokens'),'combined_output_tokens':item.get('output_tokens'),'reasoning_tokens':item.get('reasoning_tokens'),'reward':item['reward'],'source':item['source']}
        rows.append(row);solver_rows.append(row)
    for cohort in ('bedtools','deseq','biopython','skbio'):
        path='evidence/prdiff-'+cohort+'-blind-01/summary.json';d=read(path)
        assert d['attempts']==3 and d['trial_exceptions']==0
        for item in d['tasks']:
            row={'event':'prdiff-'+cohort+'/'+item['task'],'stage':'blind_native_similarity_solver','attempts':item['attempts'],'agent_episodes':item['agent_episodes'],'preserved_response_count':item['agent_episodes'],
                 'input_tokens':item['input_tokens'],'combined_output_tokens':item['output_tokens'],'reasoning_tokens':item['reasoning_tokens'],'reward':item['native_similarity_reward'],'source':path}
            rows.append(row);solver_rows.append(row)
    control_path='evidence/skbio-controls-01/summary.json';control=read(control_path);assert len(control['records'])==1
    record=control['records'][0];assert record['native_controls_passed'] is True and [x['reward'] for x in record['trials']]==[0,1]
    review_path='evidence/glm-author-budget-03/independent-review.md';review=(ROOT/review_path).read_bytes();sources[review_path]=hashlib.sha256(review).hexdigest()
    early_export={'event':'skbio-controls-01','stage':'diagnostic_derived_native_export_and_controls','recipe':'swe_smith','repository':'scikit-bio','candidate_id':record['candidate_id'],'exports_observed':1,
                  'native_rewards':[0,1],'model_calls_in_export_control_stage':0,'independent_admission':'rejected_instruction_diagnosis','solver_attempts':0,
                  'source':control_path,'authoring_source':'evidence/glm-author-budget-03/glm-report.json','independent_review':review_path,
                  'limit':'Same saved mutation as later authoring; this is a distinct rejected early exported variant, not a new source candidate or accepted task.'}
    lower={key:sum(x[key] for x in rows if isinstance(x.get(key),int)) for key in ('input_tokens','combined_output_tokens','reasoning_tokens','preserved_response_count')}
    gaps=[{'event':'code-instruct-biopython','gap':'Request/candidate/export capture unavailable; ten-candidate allowance conservatively consumed.'},
          {'event':'code-instruct-scikit-bio','gap':'Request/candidate/export capture unavailable; ten-candidate allowance conservatively consumed.'},
          {'event':'glm-author-budget-01','gap':'One reported dispatched request; response and usage not retained by the failed reporter.'},
          {'event':'dataarc-build-01','gap':'Third request dispatched without a preserved response; only two completed responses have usage.'},
          {'event':'seta-build-01','gap':'Second candidate first request timed out without a saved response; third seed unattempted.'},
          {'event':'parent-evolution-build-01','gap':'First builder request timed out without a saved response; next prepared design unattempted.'}]
    return {'stage':'retained_traffic_and_stage_reconciliation_with_explicit_gaps','observed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'records':rows,'calibration_records':calibration,
            'seed_design_records':seed_rows,'additional_early_export':early_export,'known_value_sums_lower_bounds':lower,'blind_task_attempts':sum(x['attempts'] for x in solver_rows),'observability_gaps':gaps,'source_sha256':sources,
            'limitations':['Lower-bound sums cover disjoint retained summary stages, including native-limit baseline, seed preparation, calibration and blind work. They are not complete campaign dispatched-call or token totals.',
                           'Reused authoring answers are counted once at their API-response stage; the early native export/control stage adds no model usage or new source candidate.',
                           'Agent episodes/captured metrics are not proof of every transport retry. Unknown usage and unpreserved responses remain unknown rather than zero.',
                           'Prompt tokens include repeated/cached context; summed traffic is not unique dataset tokens. Combined output includes reasoning where reported; missing reasoning breakdown stays null.',
                           'Explicit medium effort is a requested wire setting, not proof the service honored it. Effective effort/model revision and actual provider invoices are unverified.',
                           'Different native rewards and repeated lineages prevent pooled success rates or cost-per-task/yield estimates.']}


if __name__=='__main__':
    result=build();folder=ROOT/'evidence/usage-reconciliation-20261018';folder.mkdir(exist_ok=True)
    (folder/'usage.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'stage_records':len(result['records']),'blind_task_attempts':result['blind_task_attempts'],'known_value_sums_lower_bounds':result['known_value_sums_lower_bounds'],'observability_gaps':len(result['observability_gaps'])}))
