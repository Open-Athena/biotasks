"""Classify locally retained follow-up archives without publishing their bytes."""
import argparse
import hashlib
import json
from pathlib import Path
from preserve_macs_evidence import inspect_archive

ROOT=Path(__file__).resolve().parent

def sha(path):
    with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()

def main(worktrees):
    rows=[]
    for issue,folder in [(29,'29-runtime-limits'),(30,'30-script-transport'),(32,'32-runner-coverage')]:
        base=worktrees/str(issue)/'experiments'/folder
        local={sha(p):p for p in (base/'inputs-private').glob('*/outputs.tar.zst')}
        for file in sorted(base.glob('*accounting*.json')):
            account=json.loads(file.read_text());remote=account.get('output_archive')
            if not remote:continue
            row=dict(issue=issue,accounting=file.name,job_id=account['job_id'],sha256=remote['sha256'],bytes=remote['size_bytes'])
            path=local.get(remote['sha256'])
            row['local_archive_verified']=bool(path and path.stat().st_size==remote['size_bytes'])
            row['public_eligibility']='not yet reviewed'
            if 'matchms' in account['job_id']:
                row['public_eligibility']='raw Matchms excluded; retain protected original pending curated review'
                row['structural_scan']='not scanned for public upload'
            elif path:
                try:
                    members=inspect_archive(path.read_bytes(),'tar.zst')
                    row['structural_scan']='passed bounded text/archive scan'
                    row['member_count']=len(members)
                    row['member_inventory_sha256']=hashlib.sha256(json.dumps(members,sort_keys=True).encode()).hexdigest()
                except (AssertionError,UnicodeDecodeError) as exc:
                    row['structural_scan']='needs review: '+type(exc).__name__
            if path:row['local_relative_path']=str(path.relative_to(base))
            rows.append(row)
    report=dict(scope='Archive availability and structural triage only; no public-eligibility approval or upload',archives=rows,
        counts=dict(accounted=len(rows),verified_local=sum(r['local_archive_verified'] for r in rows),
            excluded_raw_matchms=sum('Matchms' in r['public_eligibility'] for r in rows),
            structural_pass=sum(r.get('structural_scan')=='passed bounded text/archive scan' for r in rows)),
        model_calls=0,remote_jobs=0)
    (ROOT/'followup-archive-inventory.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report['counts']))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--worktrees',type=Path,required=True);a=p.parse_args();main(a.worktrees)
