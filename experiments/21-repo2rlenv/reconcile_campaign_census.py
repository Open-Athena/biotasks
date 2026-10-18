"""Retrospective route/cohort census with separate generation and admission stages."""
import csv
import datetime
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parent
REPOSITORIES={'biopython':'biopython/biopython','scikit_bio':'scikit-bio/scikit-bio','bedtools2':'arq5x/bedtools2','deseq2':'thelovelab/DESeq2'}
ALIASES={**{v:v for v in REPOSITORIES.values()},'biopython':'biopython/biopython','scikit-bio':'scikit-bio/scikit-bio'}
PIPELINES={'swe_smith':'repo_mutate','swe_gen':'pr_to_env','swe_flow':'repo_reconstruct','r2e':'equivalence_tests','swe_next':'pr_runtime','r2e_gym':'commit_runtime','code_instruct':'code_instruct','seta_seed2synth':'terminal_synth','seta_evol':'task_evolve','dataarc':'terminal_synth','tmax':'terminal_synth','endless_terminals':'terminal_synth','scaler':'reasoning_synth'}
SEEDS={'seta_seed2synth':'seta-genomic-intervals-v1','seta_evol':'pr2633-parent-v1','dataarc':'pr2633-parent-v1','tmax':'tmax-biological-v1','endless_terminals':'retained-native-draws-biological-context','terminalworld':'bioinfo-notebook-v1','scaler':'synthetic-DNA-edit-distance-family','frontiersmith':'unprepared-optimization-seeds'}


def build():
    sources={}
    def read(name):
        data=(ROOT/name).read_bytes();assert len(data)<=16*1024**2
        sources[name]=hashlib.sha256(data).hexdigest()
        return json.loads(data)
    matrix_path='applicability.csv';raw=(ROOT/matrix_path).read_bytes();sources[matrix_path]=hashlib.sha256(raw).hexdigest()
    matrix=list(csv.DictReader(raw.decode().splitlines()));units={};planned=[]
    for row in matrix:
        route=row['pipeline']+'/'+row['recipe']
        if row['recipe']=='sec_bench':planned.append({'route':route,'status':'not_implemented'});continue
        if row['input_kind'] in ('repository','pr','advisory'):
            for column,repo in REPOSITORIES.items():
                key=route+'@'+repo
                units[key]={'route':route,'repository':repo,'cohort':None,'applicability_status':row[column],'generation_records':[],'current_admissions':[],'blind_results':[],'limitations':[]}
        else:
            cohort=SEEDS[row['recipe']];key=route+'@'+cohort
            units[key]={'route':route,'repository':None,'cohort':cohort,'applicability_status':row['reason'],'generation_records':[],'current_admissions':[],'blind_results':[],'limitations':[]}
    subset_path='evidence/interim-results-20261017/reconciled-subset.json';subset=read(subset_path)
    for name,digest in subset['source_sha256'].items():
        data=(ROOT/name).read_bytes();assert len(data)<=16*1024**2 and hashlib.sha256(data).hexdigest()==digest,'Interim source changed: '+name
    for record in subset['generation_rows']:
        recipe=record['recipe']
        if '/' in recipe:
            pipeline,native=recipe.split('/');assert native in ('native','native_compiled_profile');route=pipeline+'/native'
        else:route=PIPELINES[recipe]+'/'+('native' if recipe=='code_instruct' else recipe)
        target=ALIASES[record['repository']] if record.get('repository') else SEEDS[recipe]
        units[route+'@'+target]['generation_records'].append(record)
    bindings=[
        ('pr_runtime/native@scikit-bio/scikit-bio','evidence/pr2633-acceptance/acceptance.json','pr-blind-solver-01'),
        ('repo_mutate/swe_smith@biopython/biopython','evidence/lcc-acceptance-review/acceptance.json','lcc-blind-solver-01'),
        ('repo_mutate/swe_smith@scikit-bio/scikit-bio','evidence/esty-ci-acceptance/acceptance.json','esty-ci-blind-solver-01'),
        ('repo_reconstruct/swe_flow@scikit-bio/scikit-bio','evidence/observed-features-acceptance/acceptance.json','observed-features-blind-solver-01'),
        ('commit_runtime/r2e_gym@scikit-bio/scikit-bio','evidence/r2e-gym-acceptance/acceptance.json','r2e-gym-blind-solver-01')]
    for key,path,solver in bindings:
        decision=read(path);assert decision['status']=='accepted_for_bounded_pilot'
        units[key]['current_admissions'].append({'source':path,'task_id':decision['task_id'],'reward_semantics':'native_correctness','profile':decision.get('profile')})
        matches=[x for x in subset['solver_rows'] if x['run']==solver];assert len(matches)==1;units[key]['blind_results'].extend(matches)
    scaler=read('evidence/scaler-native-acceptance/summary.json');key='reasoning_synth/scaler@'+SEEDS['scaler']
    for task in scaler['tasks']:
        units[key]['current_admissions'].append({'source':'evidence/scaler-native-acceptance/summary.json','task_id':task['task_id'],'reward_semantics':'native_-1_+1_numeric_answer'})
    units[key]['blind_results']=[x for x in subset['solver_rows'] if x['run'].startswith('scaler-blind-solver-')]
    for cohort,repo in [('bedtools','arq5x/bedtools2'),('deseq','thelovelab/DESeq2'),('biopython','biopython/biopython'),('skbio','scikit-bio/scikit-bio')]:
        path='evidence/prdiff-'+cohort+'-provider-01/acceptance.json'
        if not (ROOT/path).exists():continue
        decision=read(path);assert decision['stage']=='accepted_for_bounded_similarity_pilot'
        key='pr_diff/native@'+repo
        for task,checksum in decision['task_checksums'].items():units[key]['current_admissions'].append({'source':path,'task':task,'runtime_checksum':checksum,'reward_semantics':'native_patch_similarity_not_functional_correctness'})
    legacy=read('evidence/legacy-biopython-admission-review/review.json')
    for decision in legacy['records']:
        key=decision['pipeline']+'/native@biopython/biopython';units[key]['limitations'].append({'source':'evidence/legacy-biopython-admission-review/review.json','original_bundle_decision':decision['decision'],'reason_codes':decision['reason_codes']})
    observed=sum(bool(x['generation_records']) for x in units.values())
    for key,unit in units.items():
        unit['unit_id']=key;unit['target']=3;unit['candidate_cap']=10
        unit['current_admitted_count']=len(unit['current_admissions']);unit['completed_blind_count']=len(unit['blind_results'])
        if unit['generation_records']:unit['limitations'].append('Counts belong to distinct recorded stages/profiles; do not sum repeated profiles or treat earlier admission counts as current. Unknown values stay unknown.')
    return {'stage':'retrospective_route_cohort_census_not_final_funnel','observed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'implemented_methods':len(matrix)-len(planned),'scope_entries':len(units),'units_with_retained_generation_records':observed,
            'retrospective_target_for_those_units':3*observed,'retrospective_candidate_ceiling_for_those_units':10*observed,
            'units':list(units.values()),'planned_excluded':planned,'source_sha256':sources,
            'limitations':['This is a retrospective census, not evidence that a single total N was frozen before launch; that protocol requirement was not demonstrated by retained early manifests.',
             'The 33 generation records are reconciled to all implemented methods and panel/cohort scope entries. Unsupported or blocked entries are not zero-yield generation outcomes.',
             'Admission is a later stage than generation and is kept separate. Native versus adapted exports and shared problem lineage must remain distinct.',
             'No campaign-wide exported count, acceptance yield, success rate, token total, worker time or cost-per-task is inferred. Missing request/candidate capture remains inconclusive.',
             'Active or prepared runs and later controls need their own evidence updates. This census is not a completion claim.']}


if __name__=='__main__':
    result=build();folder=ROOT/'evidence/campaign-census-20261018';folder.mkdir(exist_ok=True)
    (folder/'census.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({name:result[name] for name in ('implemented_methods','scope_entries','units_with_retained_generation_records','retrospective_target_for_those_units','retrospective_candidate_ceiling_for_those_units')}))
