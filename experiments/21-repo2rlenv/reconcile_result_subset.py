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
        reasoning = [item.get('completion_tokens_details',{}).get('reasoning_tokens') for item in items]
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
    path='evidence/r2e-skbio-author-01/summary.json';d=read(path)
    rows.append({'run':'r2e-skbio-author-01','recipe':'r2e','repository':'scikit-bio',
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
    solvers=[]
    for run in ('pr-blind-solver-01','lcc-blind-solver-01'):
        path=f'evidence/{run}/summary.json';d=read(path);u=d.get('agent_result',{})
        solvers.append({'run':run,'attempts':d['attempts'],'reward':d['reward'],
                        'input_tokens':d.get('input_tokens',u.get('n_input_tokens')),
                        'cached_input_tokens':d.get('cached_input_tokens',u.get('n_cache_tokens')),
                        'output_tokens':d.get('output_tokens',u.get('n_output_tokens')),
                        'reasoning_tokens':None,'source':path})
    return {'status':'interim_incomplete_subset','generation_rows':rows,'solver_rows':solvers,
            'source_sha256':sources,'limitations':[
                'This is not the full campaign funnel. Other generation routes, diagnostic calls, repairs outside these records and active runs are not aggregated.',
                'A null count or token value is unknown, never zero. Reserved candidate allowance is not an observed attempt count.',
                'Preserved responses do not independently establish the number of dispatched requests when request capture is incomplete.',
                'Combined output tokens include reasoning. Missing reasoning breakdown remains null.',
                'PR2633 exports share one problem lineage; do not sum them as independent biological problems.',
                'Accepted and blind counts refer to these exports; the separate portable PR-runtime profile is represented only in solver_rows.',
                'No overall yield, cost-per-task or benchmark success rate is computed from this incomplete subset.']}


if __name__=='__main__':
    result=build()
    output=ROOT/'evidence/interim-results-20261017'
    output.mkdir(exist_ok=True)
    (output/'reconciled-subset.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'generation_rows':len(result['generation_rows']),'solver_rows':len(result['solver_rows']),
                      'sources':len(result['source_sha256']),'status':result['status']}))
