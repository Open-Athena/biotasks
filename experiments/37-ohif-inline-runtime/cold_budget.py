"""Reserve before submission; reconcile one fixed attempt and unused cleanup."""
import argparse
import fcntl
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
EPIC = ROOT.parents[2]/'33/experiments/33-unattended-validation'
RUN = 'biotasks37-ohif-5996-inline-001'


def write(path, data):
    temporary = path.with_suffix('.pending')
    temporary.write_text(json.dumps(data, indent=2)+'\n')
    temporary.replace(path)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['reserve', 'reconcile'])
    action = parser.parse_args().action
    with (EPIC/'private/budget-update.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        budget = json.loads((EPIC/'budget.json').read_text())
        admissions = [e for e in budget['events'] if e['kind'] == 'reserved_cpu_admission']
        if action == 'reserve':
            assert not any(e.get('run_id', '').startswith('biotasks37-') for e in admissions)
            assert budget['additional_allocated_cpu_hours']+budget['outstanding_cpu_hour_reservations']+6+1/6 <= 32
            for run, maximum in [(RUN, 6), (RUN+'-cleanup', 1/6)]:
                budget['events'].append(dict(kind='reserved_cpu_admission', run_id=run,
                    maximum_allocated_cpu_hours=maximum, new_paid_capacity=False,
                    state='reserved before submission', child_issue=37, child_total_ceiling_cpu_hours=8))
            write(ROOT/'cold-cpu-reservation.json', dict(run_id=RUN, maximum_cpu_hours=6,
                reservation_state='booked in epic 33 budget before submission',
                prior_child_allocated_cpu_hours=0, child_ceiling_cpu_hours=8,
                epic_ceiling_cpu_hours=32, cleanup_allowance_cpu_hours=1/6))
        else:
            account = json.loads((ROOT/'cold-accounting.json').read_text())
            assert account['job_id'] == '/exedev/'+RUN and account['attempts'] == 1
            event = next(e for e in admissions if e['run_id'] == RUN)
            actual = account['allocated_cpu_hours']
            assert 0 <= actual <= event['maximum_allocated_cpu_hours']
            event.update(state='terminal reconciled', actual_allocated_cpu_hours=actual)
            result = json.loads((ROOT/'inputs-private/cold-output/control-result.json').read_text())
            if result.get('cleanup', {}).get('verified_empty'):
                cleanup = next(e for e in admissions if e['run_id'] == RUN+'-cleanup')
                assert cleanup['state'] in ('reserved before submission', 'released unused')
                cleanup.update(state='released unused', reason='Primary job verified owned resources empty; no cleanup attempt submitted')
        admissions = [e for e in budget['events'] if e['kind'] == 'reserved_cpu_admission']
        budget['additional_allocated_cpu_hours'] = sum(e['actual_allocated_cpu_hours'] for e in admissions if e['state'] == 'terminal reconciled')
        budget['outstanding_cpu_hour_reservations'] = sum(e['maximum_allocated_cpu_hours'] for e in admissions if e['state'] == 'reserved before submission')
        write(EPIC/'budget.json', budget)
        print(json.dumps({k: budget[k] for k in ['additional_allocated_cpu_hours', 'outstanding_cpu_hour_reservations', 'new_model_calls']}))


if __name__ == '__main__':
    main()
