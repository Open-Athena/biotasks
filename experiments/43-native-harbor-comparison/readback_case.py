"""Component observations; absent samples never prove process termination."""
from datetime import datetime,timezone


def epoch_ns(value):
    if not value:return None
    parsed=datetime.fromisoformat(value.replace('Z','+00:00'))
    if parsed.tzinfo is None:parsed=parsed.replace(tzinfo=timezone.utc)
    delta=parsed-datetime(1970,1,1,tzinfo=timezone.utc)
    return (delta.days*86400+delta.seconds)*1000000000+delta.microseconds*1000


def deadline_observations(trial,observations,events):
    timing=trial.get('verifier') or {};error=trial.get('exception_info') or {}
    native=epoch_ns(timing.get('finished_at')) or epoch_ns(error.get('occurred_at'))
    field='verifier.finished_at' if timing.get('finished_at') else 'exception_info.occurred_at'
    post=[];samples=[]
    for observation in observations:
        if observation.get('state')!='sampled':continue
        samples.append(observation)
        for row in observation['processes']:
            actual=row['observed'];same=actual.get('pid')==row['expected_pid'] and actual.get('start_ticks')==row['expected_start_ticks']
            live=bool(same and actual.get('writer_command') and actual.get('state') not in [None,'Z','X'])
            if native and observation['observed_start_ns']>native and live:
                post.append(dict(pid=actual['pid'],start_ticks=actual['start_ticks'],state=actual['state'],
                    observation_start_ns=observation['observed_start_ns'],observation_finish_ns=observation['observed_finished_ns'],
                    seconds_after_native_verifier_end=(observation['observed_start_ns']-native)/1e9,fd1_inode=actual['fd1_inode'],fd1_offset=actual['fd1_offset']))
    lifecycle=[e for e in events if e.get('Type')=='container' and e.get('Action') in ['kill','die','stop','destroy']]
    return dict(native_verifier_end_epoch_ns=native,native_verifier_end_field=field if native else None,
        timestamp_policy='Controller and task TZ=UTC; timezone-naive native exception timestamps interpreted as UTC.',
        live_writer_after_native_verifier_end_observed=bool(post),post_deadline_live_samples=post,
        observer_successful_samples=len(samples),observer_unavailable_samples=sum(o.get('state') in ['exec_unavailable','observer_exec_timeout'] for o in observations),
        observer_hole_samples=sum(o['log_nul_bytes']>0 for o in samples),observer_maximum_nul_bytes=max((o['log_nul_bytes'] for o in samples),default=0),
        lifecycle_events=[dict(action=e['Action'],time_ns=e.get('timeNano'),seconds_after_native_verifier_end=(e['timeNano']-native)/1e9 if native and e.get('timeNano') else None,attributes=e.get('Actor',{}).get('Attributes',{})) for e in lifecycle],
        absence_of_live_sample_proves_termination=False)
