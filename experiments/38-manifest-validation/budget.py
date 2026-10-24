"""Idempotent family admissions and actual-allocation reconciliation."""
import json
from pathlib import Path

from common import json_sha,write
from resume_runner import controller_lock


class Budget:
    def __init__(self,path):self.path=Path(path)

    def update_totals(self,budget):
        events=[e for e in budget['events'] if e['kind']=='reserved_cpu_admission']
        budget['additional_allocated_cpu_hours']=sum(e['actual_allocated_cpu_hours'] for e in events if e['state']=='terminal reconciled')
        budget['outstanding_cpu_hour_reservations']=sum(e['maximum_allocated_cpu_hours'] for e in events if e['state']=='reserved before submission')
        assert budget['additional_allocated_cpu_hours']+budget['outstanding_cpu_hour_reservations']<=budget['additional_reserved_cpu_hour_ceiling']+1e-9

    def admit(self,family,path):
        run=family['run_id'];resources=family['resources'];maximum=resources['maximum_cpu_hours']
        with controller_lock(self.path.parent/'private/budget-update'):
            budget=json.loads(self.path.read_text())
            assert budget['new_paid_capacity_allowed'] is False and budget['paid_model_execution_enabled'] is False
            assert maximum>0 and resources['cpus']==2
            pairs=[(run,maximum),(run+'-cleanup',resources['cleanup_allowance_cpu_hours'])]
            existing={e.get('run_id'):e for e in budget['events'] if e['kind']=='reserved_cpu_admission'}
            if any(name in existing for name,_ in pairs):
                assert all(name in existing and existing[name]['maximum_allocated_cpu_hours']==value for name,value in pairs)
            else:
                bound=sum(value for _,value in pairs)
                assert budget['additional_allocated_cpu_hours']+budget['outstanding_cpu_hour_reservations']+bound<=32
                for name,value in pairs:
                    budget['events'].append(dict(kind='reserved_cpu_admission',run_id=name,child_issue=38,
                        maximum_allocated_cpu_hours=value,new_paid_capacity=False,state='reserved before submission'))
                self.update_totals(budget);write(self.path,budget)
            receipt=dict(run_id=run,maximum_cpu_hours=maximum,cleanup_cpu_hours=resources['cleanup_allowance_cpu_hours'],
                source_family_sha256=family['source_family_sha256'],admitted_before_submission=True,model_calls=0,new_capacity=False)
            if Path(path).exists():assert json.loads(Path(path).read_text())==receipt
            else:write(path,receipt)
        return receipt

    def verify_reserved(self,run):
        budget=json.loads(self.path.read_text())
        event=next(e for e in budget['events'] if e.get('run_id')==run)
        assert event['state']=='reserved before submission'
        self.update_totals(budget)

    def reconcile(self,account):
        run=account['job_id'].removeprefix('/exedev/')
        with controller_lock(self.path.parent/'private/budget-update'):
            budget=json.loads(self.path.read_text());event=next(e for e in budget['events'] if e.get('run_id')==run)
            actual=account['allocated_cpu_hours'];assert actual>=0
            if event['state']=='terminal reconciled':assert event['actual_allocated_cpu_hours']==actual
            else:
                assert event['state']=='reserved before submission'
                event.update(state='terminal reconciled',actual_allocated_cpu_hours=actual)
            # Always record actual usage, including any overshoot, before stopping.
            admissions=[e for e in budget['events'] if e['kind']=='reserved_cpu_admission']
            budget['additional_allocated_cpu_hours']=sum(e['actual_allocated_cpu_hours'] for e in admissions if e['state']=='terminal reconciled')
            budget['outstanding_cpu_hour_reservations']=sum(e['maximum_allocated_cpu_hours'] for e in admissions if e['state']=='reserved before submission')
            write(self.path,budget)
            assert actual<=event['maximum_allocated_cpu_hours'] and budget['additional_allocated_cpu_hours']+budget['outstanding_cpu_hour_reservations']<=32

    def release_cleanup(self,run,proof):
        assert proof.get('verified_empty') or proof.get('verified_no_creation')
        with controller_lock(self.path.parent/'private/budget-update'):
            budget=json.loads(self.path.read_text());event=next(e for e in budget['events'] if e.get('run_id')==run+'-cleanup')
            assert event['state'] in ('reserved before submission','released unused')
            event.update(state='released unused',reason='Primary cleanup or bound no-creation proof verified; no cleanup attempt submitted',proof_sha256=json_sha(proof))
            self.update_totals(budget);write(self.path,budget)
