"""One serial invocation, durable per-family stages, unchanged stage journal."""
import argparse
from contextlib import contextmanager
import json
import os
from pathlib import Path
import time

import backend
from budget import Budget
from common import sha,write
from collect import readback,cleanup_readback
import preserve
from resume_runner import advance,controller_lock

ROOT=Path(__file__).resolve().parent


class Adapter:
    def __init__(self,family,client,budget):
        self.family,self.directory,self.files=backend.load(family['id'])
        assert self.family==family
        self.client=client;self.budget=Budget(budget)

    def bind(self,*names):return [dict(path=str(self.directory/n),sha256=sha(self.directory/n)) for n in names]

    def probe(self,stage):
        paths=dict(candidate_verified='candidate.json',submission_recorded='submission.json',remote_terminal='accounting.json',
            archive_readback_verified='readback.json',public_eligibility_reviewed='manifest.json',hf_readback_verified='hf-receipt.json',
            cleanup_terminal='cleanup-proof.json',cleanup_verified='complete.json')
        path=self.directory/paths[stage]
        if stage=='submission_recorded' and path.exists():
            value=json.loads(path.read_text())
            if value['state']=='submission_pending':
                state=backend.observe(self.client,self.family,self.directory)
                if state=='handle_missing':return dict(state='pending')
        if stage=='remote_terminal' and not path.exists():
            backend.observe(self.client,self.family,self.directory)
            if not path.exists():return dict(state='pending')
        return dict(state='ready',evidence=self.bind(paths[stage])) if path.exists() else dict(state='absent')

    def verify(self,stage,evidence):
        family=self.family;d=self.directory
        if stage=='candidate_verified':
            value=json.loads((d/'candidate.json').read_text())
            assert value['run_id']==family['run_id'] and value['payload_sha256']==family['payload_sha256']
            assert json.loads((d/'admission.json').read_text())['source_family_sha256']==family['source_family_sha256']
        elif stage=='submission_recorded':
            row=json.loads((d/'submission.json').read_text())
            assert row['state'] in ('submitted','observed_existing') and row['payload_sha256']==family['payload_sha256']
        elif stage=='remote_terminal':
            row=json.loads((d/'accounting.json').read_text());assert row['attempts']==1
            self.budget.reconcile(row)
        elif stage=='archive_readback_verified':
            row=json.loads((d/'readback.json').read_text())
            assert row['run_id']==family['run_id'] and row['archive_sha256']==sha(d/'output/outputs.tar.zst')
            assert row['input_package_verified']
        elif stage=='public_eligibility_reviewed':preserve.verify_stage(d)
        elif stage=='hf_readback_verified':preserve.verified_receipt(d)
        elif stage=='cleanup_terminal':
            proof=json.loads((d/'cleanup-proof.json').read_text())
            assert proof['run_id']==family['run_id'] and (proof['cleanup'].get('verified_empty') or proof['cleanup'].get('verified_no_creation'))
        elif stage=='cleanup_verified':
            proof=json.loads((d/'cleanup-proof.json').read_text())
            final=json.loads((d/'complete.json').read_text());assert final['cleanup_proof_sha256']==sha(d/'cleanup-proof.json')
            assert final['hf_manifest_sha256']==preserve.verified_receipt(d)['manifest_sha256']
            if proof['route']=='emergency':preserve.verified_receipt(d/'cleanup')
        else:raise ValueError(stage)

    def perform(self,stage):
        f=self.family;d=self.directory
        if stage=='candidate_verified':
            self.budget.admit(f,d/'admission.json')
            row=backend.submit(self.client,f,d,self.files,self.budget.path,preflight=True)
            write(d/'candidate.json',row)
        elif stage=='submission_recorded':backend.submit(self.client,f,d,self.files,self.budget.path)
        elif stage=='archive_readback_verified':readback(f,d)
        elif stage=='public_eligibility_reviewed':preserve.prepare(f,d)
        elif stage=='hf_readback_verified':preserve.publish(d)
        elif stage=='cleanup_terminal':self.cleanup()
        elif stage=='cleanup_verified':
            proof=json.loads((d/'cleanup-proof.json').read_text())
            if proof['route']=='emergency':
                cf,cd,_=backend.load(f['id'],cleanup=True);preserve.prepare(cf,cd,cleanup=True);preserve.publish(cd)
            write(d/'complete.json',dict(run_id=f['run_id'],cleanup_proof_sha256=sha(d/'cleanup-proof.json'),
                hf_manifest_sha256=preserve.verified_receipt(d)['manifest_sha256'],model_calls=0))
        else:raise ValueError(stage)

    def recover(self,stage):
        if stage=='submission_recorded':
            # A persisted network intent is queried only. A journal intent before any
            # backend intent is safe to continue in this same-process adapter.
            if (self.directory/'submission.json').exists():backend.observe(self.client,self.family,self.directory)
            else:self.perform(stage)
        else:self.perform(stage)

    def cleanup(self):
        d=self.directory;f=self.family;result=json.loads((d/'readback.json').read_text());proof=result.get('cleanup') or {}
        if proof.get('verified_empty') or proof.get('verified_no_creation'):
            assert not (d/'cleanup/submission.json').exists()
            self.budget.release_cleanup(f['run_id'],proof)
            write(d/'cleanup-proof.json',dict(run_id=f['run_id'],route='primary',cleanup=proof))
            return
        # Missing task archive could mean the volume is the only copy. Do not delete it.
        assert result['task_package_verified'], 'Preserve owned volume: task execution evidence not fully copied'
        cf,cd,files=backend.load(f['id'],cleanup=True)
        if not (cd/'submission.json').exists():
            backend.submit(self.client,cf,cd,files,self.budget.path,preflight=True)
            backend.submit(self.client,cf,cd,files,self.budget.path)
        backend.observe(self.client,cf,cd)
        if not (cd/'accounting.json').exists():return
        self.budget.reconcile(json.loads((cd/'accounting.json').read_text()))
        read=cleanup_readback(cf,cd)
        write(d/'cleanup-proof.json',dict(run_id=f['run_id'],route='emergency',cleanup=read['cleanup']))


def journal_plan(family):
    # Bind executable and policy code, rather than just a mutable run name.
    names=sorted({p.name for p in ROOT.glob('*.py')}|{'cohort.json','runtime-plan.json','public-policy.json',
        'archive-client-profile.json','control-pins.json','setup_controller.sh'})
    return dict(run_id=family['run_id'],inputs=[dict(path=str(ROOT/name),sha256=sha(ROOT/name)) for name in names])


def run_once(client,budget):
    plan=json.loads((ROOT/'runtime-plan.json').read_text())
    assert plan['model_calls_enabled'] is False and plan['new_capacity_allowed'] is False
    for family in plan['families']:
        if family['mode']=='reference_stop':continue
        adapter=Adapter(family,client,budget);p=journal_plan(family)
        state=advance(p,adapter.directory/'journal.json',adapter)
        if state!='complete':return dict(family=family['id'],state=state)
    return dict(state='complete')


@contextmanager
def connect(config):
    from iris.cli.connect import connect_controller
    from iris.client.client import IrisClient
    with connect_controller(config_file=config) as endpoint:
        with IrisClient.remote(endpoint.url,credentials=endpoint.credentials,timeout_ms=30000) as client:yield client


def load_credentials():
    # Approved CW credentials enter only the local transport, never payloads.
    path=Path('/home/exedev/.config/coreweave/credentials.env')
    if not os.environ.get('CW_KEY_ID') or not os.environ.get('CW_KEY_SECRET'):
        import shlex
        for line in path.read_text().splitlines():
            words=shlex.split(line)
            if not words or words[0].startswith('#'):continue
            if words[0]=='export':words=words[1:]
            if len(words)==1 and '=' in words[0]:
                name,value=words[0].split('=',1)
                if name in ('CW_KEY_ID','CW_KEY_SECRET') and not os.environ.get(name):os.environ[name]=value


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--config',type=Path,required=True)
    parser.add_argument('--budget',type=Path,required=True);parser.add_argument('--watch',action='store_true');args=parser.parse_args()
    load_credentials()
    with controller_lock(ROOT/'private/cohort-controller'):
        while True:
            with connect(args.config) as client:state=run_once(client,args.budget)
            print(json.dumps(dict(observed=time.time(),**state)),flush=True)
            if state['state']=='complete' or not args.watch:return
            if state['state'].startswith(('waiting:','recovering:')):time.sleep(300)


if __name__=='__main__':main()
