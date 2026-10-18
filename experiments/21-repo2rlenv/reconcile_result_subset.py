"""Evidence-linked interim counts; deliberately not a whole-campaign yield."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def build():
    sources = {}
    def read(path):
        raw = (ROOT/path).read_bytes()
        sources[path] = hashlib.sha256(raw).hexdigest()
        return json.loads(raw)
    def tokens(items):
        def total(key):
            values = [item.get(key) for item in items]
            return sum(values) if values and all(isinstance(v,int) for v in values) else None
        reasoning = [(item.get('completion_tokens_details') or {}).get('reasoning_tokens',item.get('reasoning_tokens')) for item in items]
        return {'input_tokens':total('prompt_tokens'), 'combined_output_tokens':total('completion_tokens'),
                'reasoning_tokens':sum(reasoning) if reasoning and all(isinstance(v,int) for v in reasoning) else None}
    rows = []
    for run, recipe, repo in [
        ('swe-gen-skbio-01','swe_gen','scikit-bio'),
        ('swe-next-skbio-01','swe_next','scikit-bio'),
        ('r2e-gym-skbio-fixtures-02','r2e_gym','scikit-bio'),
        ('swe-gen-biopython-01','swe_gen','biopython')]:
        path=f'evidence/{run}/summary.json';d=read(path)
        if 'authoring' in d:
            count=d['authoring']['calls'];usage=[d['authoring']['usage']]
        elif 'authoring_calls' in d:
            count=d['authoring_calls'];usage=[x['usage'] for x in d['authoring_usage']]
        else:
            count=d['model_calls'];usage=[d['usage']]
        rows.append({'run':run,'recipe':recipe,'repository':repo,
                     'lineage_group':'biopython-pr5317' if repo=='biopython' else 'scikit-bio-pr2633',
                     'candidates':d.get('candidates',d.get('eligible_candidates')),
                     'exports':d.get('exports',d.get('exported_tasks')),
                     'accepted':d['independently_accepted_tasks'],
                     'blind_attempts':d.get('blind_attempts',d.get('blind_solver_attempts')),
                     'preserved_model_responses':count,**tokens(usage),'source':path})
    path='evidence/swe-next-biopython-01/summary.json';d=read(path)
    rows.append({'run':'swe-next-biopython-01','recipe':'swe_next','repository':'biopython',
                 'lineage_group':'biopython-pr5317','candidates':d['candidates_considered'],
                 'eligible_candidates':d['eligible_candidates'],'exports':d['exports'],
                 'accepted':d['independently_accepted_tasks'],'blind_attempts':d['blind_solver_attempts'],
                 'preserved_model_responses':d['authoring_calls'],
                 'input_tokens':0,'combined_output_tokens':0,'reasoning_tokens':0,
                 'candidate_allowance_consumed':d['candidate_allowance_consumed'],
                 'remaining_first_pass_candidate_allowance':d['remaining_first_pass_candidate_allowance'],
                 'outcome':d['stage'],'source':path})
    path='evidence/r2e-gym-biopython-01/summary.json';d=read(path)
    rows.append({'run':'r2e-gym-biopython-01','recipe':'r2e_gym','repository':'biopython',
                 'lineage_group':'biopython-qcp-history-profile',
                 'history_records_considered':d['history_records_considered'],
                 'eligible_candidates':d['eligible_candidates'],'exports':d['exports'],
                 'accepted':d['independently_accepted_tasks'],'blind_attempts':d['blind_solver_attempts'],
                 'preserved_model_responses':d['authoring_calls'],
                 'input_tokens':0,'combined_output_tokens':0,'reasoning_tokens':0,
                 'scope':'Source-filtered history records are distinct from eligible generation candidates',
                 'outcome':d['stage'],'source':path})
    for run,repo in [('r2e-skbio-author-01','scikit-bio'),('r2e-biopython-author-01','biopython')]:
        path=f'evidence/{run}/summary.json';d=read(path)
        rows.append({'run':run,'recipe':'r2e','repository':repo,
                     'candidates':d['candidate_result']['candidates'],'exports':d['candidate_result']['emitted'],
                     'accepted':d['independently_accepted_tasks'],'blind_attempts':d['blind_solver_attempts'],
                     'preserved_model_responses':d['model_responses'],**tokens([d['usage']]),'source':path})
    path='evidence/tmax-biological-02/tmax-result.json';d=read(path)
    usage_path='evidence/tmax-biological-02/model-usage.json';u=read(usage_path)
    rows.append({'run':'tmax-biological-02','recipe':'tmax','repository':None,
                 'candidates':d['candidates'],'exports':d['emitted'],
                 'preserved_model_responses':len(u['calls']),**tokens([x['usage'] for x in u['calls']]),
                 'source':path,'usage_source':usage_path})
    path='evidence/endless-biological-02/summary.json';d=read(path)
    usage_path='evidence/endless-biological-02/model-usage.json';u=read(usage_path)
    rows.append({'run':'endless-biological-02','recipe':'endless_terminals','repository':None,
                 'candidates':d['candidates'],'exports':d['exports'],
                 'accepted':d['independently_accepted_tasks'],'blind_attempts':d['blind_solver_attempts'],
                 'preserved_model_responses':d['preserved_model_responses'],
                 **tokens([x['usage'] for x in u['calls']]),'source':path,'usage_source':usage_path})
    path='evidence/parent-evolution-build-01/result-summary.json';d=read(path)
    rows.append({'run':'parent-evolution-build-01','recipe':'seta_evol','repository':None,
                 'candidate_builds_started':d['candidate_builds_started'],
                 'saved_designs_available':d['saved_schema_valid_designs'],
                 'exports':d['exports'],'accepted':d['independently_accepted'],'blind_attempts':d['solver_attempts'],
                 'dispatched_model_requests':d['dispatched_builder_requests'],
                 'preserved_model_responses':d['completed_builder_responses'],
                 'input_tokens':None,'combined_output_tokens':None,'reasoning_tokens':None,
                 'source':path,'scope':'Materialization only; excludes earlier design generation','missing_usage_reason':d['usage']})
    path='evidence/code-instruct-capture-diagnosis/candidate-budget-reconciliation.json';d=read(path)
    for cohort in d['cohorts']:
        rows.append({'run':'code-instruct-'+cohort['repository'],'recipe':'code_instruct','repository':cohort['repository'],
                     'candidates':cohort['actual_candidates_attempted'],'exports':None,
                     'accepted':cohort['independently_accepted_tasks'],'blind_attempts':cohort['blind_attempts'],
                     'preserved_model_responses':None,'input_tokens':None,'combined_output_tokens':None,'reasoning_tokens':None,
                     'candidate_allowance_consumed':cohort['candidate_allowance_conservatively_consumed'],
                     'source':path,'outcome':cohort['outcome']})
    for run,recipe,repo,export_run,contrast_run in [
        ('biopython-author-02','swe_smith','biopython','biopython-smith-controls-02','biopython-smith-02'),
        ('skbio-author-03','swe_smith','scikit-bio','skbio-smith-controls-02','skbio-smith-02'),
        ('biopython-flow-author-01','swe_flow','biopython','biopython-flow-controls-01',None),
        ('skbio-flow-author-01','swe_flow','scikit-bio','skbio-flow-controls-01',None)]:
        path=f'evidence/{run}/summary.json';author=read(path)
        export_path=f'evidence/{export_run}/summary.json';export=read(export_path)
        outcomes=author['records'];calls=author['raw_calls']
        exported_ids=([x['candidate_id'] for x in export['records']]
                      if 'records' in export else [export['candidate_id']])
        assert set(exported_ids)<=set(x['candidate_id'] for x in outcomes)
        row={'run':run,'recipe':recipe,'repository':repo,
             'authoring_candidates_attempted':len(outcomes),
             'schema_valid_authored':sum(x['status']=='authored' for x in outcomes),
             'authoring_candidate_ids':[x['candidate_id'] for x in outcomes],
             'exports':len(exported_ids),'exported_candidate_ids':exported_ids,
             'preserved_model_responses':len(calls),**tokens([x['usage'] for x in calls]),
             'source':path,'export_source':export_path,
             'scope':'Joins saved candidate authoring to subsequent native exports; repeated validation/adaptations are not new generated candidates. Earlier token-limit diagnostic calls are excluded.'}
        if contrast_run:
            contrast_path=f'evidence/{contrast_run}/summary.json';contrast=read(contrast_path)
            row.update(mutation_candidates_attempted=contrast['attempted'],
                       executable_mutation_contrasts=contrast['execution_passed'],
                       contrast_source=contrast_path)
        else:
            row['pre_authoring_candidate_attempts']=None
            row['pre_authoring_attempt_limit']='Not inferred from the three selected authoring records'
        rows.append(row)
    solvers=[]
    for run in ('pr-blind-solver-01','lcc-blind-solver-01','scaler-blind-solver-01','scaler-blind-solver-02','scaler-blind-solver-03','r2e-gym-blind-solver-01'):
        path=f'evidence/{run}/summary.json';d=read(path);u=d.get('agent_result',{})
        solvers.append({'run':run,'attempts':d['attempts'],'reward':d['reward'],
                        'input_tokens':d.get('input_tokens',u.get('n_input_tokens')),
                        'cached_input_tokens':d.get('cached_input_tokens',u.get('n_cache_tokens')),
                        'output_tokens':d.get('output_tokens',u.get('n_output_tokens')),
                        'reasoning_tokens':None,'source':path})
    validations=[]
    for run,recipe,repo,lineage in [
        ('strong-independent-01','swe_smith','scikit-bio','scikit-bio-strong-reconstruction'),
        ('esty_ci-independent-02','swe_smith','scikit-bio','scikit-bio-esty-ci-reconstruction'),
        ('gc-skew-independent-01','swe_flow','biopython','biopython-gc-skew-reconstruction')]:
        path=f'evidence/{run}/review.json';review=read(path)
        controls_path=f'evidence/{run}/native-summary.json';controls=read(controls_path)
        validations.append({'run':run,'recipe':recipe,'repository':repo,'lineage_group':lineage,
                            'outcome':review['acceptance'],'solver_eligible':review['solver_eligible'],
                            'model_calls':review['model_calls'],
                            'native_controls':[{'case':x['case'],'completed':x['completed'],'reward':x['reward'],
                                                'expected_reward':x['expected_reward']} for x in controls['records']],
                            'source':path,'control_source':controls_path})
    path='evidence/biopython-flow-controls-01/summary.json';failed=read(path)
    validations.append({'run':'biopython-flow-controls-01','recipe':'swe_flow','repository':'biopython',
                        'lineage_group':'biopython-gc-skew-reconstruction','outcome':failed['stage'],
                        'model_calls':failed['model_calls'],'native_trials_completed':failed['native_trials_completed'],
                        'native_controls':failed['trials'],'source':path})
    path='evidence/biopython-flow-controls-02/native-summary.json';corrected=read(path)
    records=corrected['records'];assert len(records)==1
    validations.append({'run':'biopython-flow-controls-02','recipe':'swe_flow','repository':'biopython',
                        'lineage_group':'biopython-gc-skew-reconstruction',
                        'outcome':'native_contrast_passed_independent_acceptance_pending',
                        'model_calls':0,'native_controls':[{'case':x['agent'],'completed':x['completed'],
                                                           'reward':x['reward']} for x in records[0]['trials']],
                        'adaptation':'Idempotent LICENSE bootstrap assertion; unchanged instruction and tests',
                        'source':path})
    path='evidence/esty_ci-independent-01/summary.json';failed=read(path)
    validations.append({'run':'esty_ci-independent-01','recipe':'swe_smith','repository':'scikit-bio',
                        'lineage_group':'scikit-bio-esty-ci-reconstruction','outcome':failed['status'],
                        'model_calls':failed['model_calls'],'native_trials_completed':failed['controls_executed'],
                        'reward':failed['reward'],'source':path})
    for run in ('scaler-provider-01','scaler-provider-02','scaler-provider-03'):
        path=f'evidence/{run}/status.json';provider=read(path)
        validations.append({'run':run,'recipe':'scaler','repository':None,
                            'lineage_group':'synthetic-dna-edit-distance','outcome':provider['status'],
                            'model_calls':provider['model_calls'],
                            'native_controls':[{'case':x['agent'],'reward':x['result']['verifier_result']['rewards']['reward'],
                                                'task_checksum':x['result']['task_checksum']} for x in provider['cases']],
                            'source':path})
    for run, recipe, lineage in [('swegen-provider-01','swe_gen','scikit-bio-pr2633'),
                                 ('swe-next-provider-01','swe_next','scikit-bio-pr2633'),
                                 ('r2e-gym-provider-01','r2e_gym','scikit-bio-pr2633'),
                                 ('esty-ci-provider-01','swe_smith','scikit-bio-esty-ci-reconstruction'),
                                 ('observed-features-provider-01','swe_flow','scikit-bio-observed-features-reconstruction')]:
        path=f'evidence/{run}/status.json';provider=read(path)
        summary_path=f'evidence/{run}/summary.json';summary=read(summary_path)
        validations.append({'run':run,'recipe':recipe,'repository':'scikit-bio',
                        'lineage_group':lineage,'outcome':summary['status'],
                        'model_calls':provider['model_calls'],
                        'native_controls':[{'case':x['agent'],'reward':x['result']['verifier_result']['rewards']['reward'],
                                            'task_checksum':x['result']['task_checksum']} for x in provider['cases']],
                        'source':path,'summary_source':summary_path})
    acceptance_reviews=[]
    for path in ['evidence/history-final-acceptance/swe-gen-skbio-01/review.json',
                 'evidence/history-final-acceptance/swe-next-skbio-01/review.json',
                 'evidence/qcp-final-acceptance/review.json',
                 'evidence/r2e-gym-acceptance/acceptance.json',
                 'evidence/esty-ci-acceptance/acceptance.json']:
        review=read(path)
        acceptance_reviews.append({'task':review['task'],'status':review['status'],
                                   'solver_eligible':review['solver_eligible'],'source':path})
    return {'status':'interim_incomplete_subset','generation_rows':rows,'solver_rows':solvers,'validation_rows':validations,
            'acceptance_reviews':acceptance_reviews,'source_sha256':sources,'limitations':[
                'This is not the full campaign funnel. Other generation routes, diagnostic calls, repairs outside these records and active runs are not aggregated.',
                'A null count or token value is unknown, never zero. Reserved candidate allowance is not an observed attempt count.',
                'Preserved responses do not independently establish the number of dispatched requests when request capture is incomplete.',
                'Combined output tokens include reasoning. Missing reasoning breakdown remains null.',
                'PR2633 exports share one problem lineage; do not sum them as independent biological problems.',
                'Generation and solver rows are not joined into a campaign-wide acceptance denominator; the accepted portable PR-runtime and LCC tasks appear only in solver_rows.',
                'Validation rows are repeated controls or export adaptations, not additional generation candidates or independent problems.',
                'No overall yield, cost-per-task or benchmark success rate is computed from this incomplete subset.']}


if __name__=='__main__':
    result=build()
    output=ROOT/'evidence/interim-results-20261017'
    output.mkdir(exist_ok=True)
    (output/'reconciled-subset.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'generation_rows':len(result['generation_rows']),'solver_rows':len(result['solver_rows']),
                      'validation_rows':len(result['validation_rows']),'sources':len(result['source_sha256']),'status':result['status']}))
