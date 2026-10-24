"""Report component observations without changing the preregistered conjunction."""
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from common import sha,write


def main():
    source=ROOT/'private/harbor_timeout/readback.json'
    result=json.loads(source.read_text())
    finite=next(c for c in result['cases'] if c['name']=='finite')
    timeout=next(c for c in result['cases'] if c['name']=='timeout')
    assert result['finite_control_passed'] and result['native_timeout_observed']
    events=timeout['events'];starts=[e for e in events if e['event']=='start']
    assert len(starts)==2
    origin=starts[0]['wall_ns']
    holes=[e for e in events if e['event']=='sample' and e['log_nul_bytes']>0]
    live=[e for e in timeout['live_prior_writers'] if e['same_start_ticks'] and e['same_log_inode'] and e['prior_offset_exceeds_new_offset'] and e['new_offset']==0]
    timeline=[]
    tokens={e['token']:i for i,e in enumerate(starts)}
    for event in events:
        row=dict(seconds_since_first_writer_start=(event['wall_ns']-origin)/1e9,writer_index=tokens[event['token']],event=event['event'])
        if event['event']=='sample':row.update(log_bytes=event['log_bytes'],nul_bytes=event['log_nul_bytes'],writer_offset=event['self'].get('fd1_offset'))
        timeline.append(row)
    value=dict(issue=41,analysis_kind='post_run_component_observations',readback_sha256=sha(source),
        finite_control_passed=result['finite_control_passed'],native_timeout_observed=result['native_timeout_observed'],
        live_prior_writer_confirmed=bool(live),live_prior_writer=live,
        retry_writer_started_seconds=(starts[1]['wall_ns']-origin)/1e9,
        transient_in_container_holes_observed=bool(holes),hole_sample_count=len(holes),
        maximum_observed_nul_bytes=max((e['log_nul_bytes'] for e in holes),default=0),
        first_hole_sample_seconds=(holes[0]['wall_ns']-origin)/1e9 if holes else None,
        last_hole_sample_seconds=(holes[-1]['wall_ns']-origin)/1e9 if holes else None,
        final_saved_log_nul_bytes=timeout['raw_log_nul_bytes'],
        preregistered_full_mechanism_observed=result['fixture_mechanism_observed'],
        original_metric_unchanged=True,historical_scanpy_cause_proven=False,
        interpretation='Live first writer survives into native retry; truncation on the same inode resets only the new descriptor. In-container samples observe transient holes. The new writer later fills the initial gap, so the final archive has no NULs and the predeclared conjunction requiring final NULs remains false.',
        limitation='Synthetic fixed-record fixture on one worker; sampled counts/hashes and raw final log, not retained full intermediate file snapshots. Does not identify historical Scanpy cause or validate that task.',
        timeline=timeline,model_calls=0,new_biological_tasks=0)
    assert not value['preregistered_full_mechanism_observed'] and value['final_saved_log_nul_bytes']==0
    write(ROOT/'component-observations.json',value)
    print(json.dumps({k:v for k,v in value.items() if k not in ['timeline','live_prior_writer','interpretation','limitation']}))


if __name__=='__main__':main()
