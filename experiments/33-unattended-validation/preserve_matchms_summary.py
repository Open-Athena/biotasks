"""Public numeric/provenance summary; never copy restricted raw Matchms bytes."""
import argparse
import datetime
import hashlib
import json
from pathlib import Path
from preserve_followup_evidence import publish
ROOT=Path(__file__).resolve().parent
SCOPE='matchms_followup_numeric_outcomes_and_provenance_only'

def prepare(worktrees):
    target=ROOT/'private/matchms-summary-snapshot';assert not target.exists();target.mkdir()
    files=[]
    def stage(name,data):
        raw=(json.dumps(data,indent=2)+'\n').encode();(target/name).write_bytes(raw)
        files.append(dict(path=name,bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest()))
    for issue,folder,filename in [(29,'29-runtime-limits','matchms-control-results.json'),(30,'30-script-transport','live-readback.json'),(32,'32-runner-coverage','live-readback.json')]:
        source=worktrees/str(issue)/'experiments'/folder/filename
        raw=source.read_bytes();data=json.loads(raw)
        keys=['task','agent','state','reward','parse_status','resolved','command_resolved','test_exit_code','f2p_passed','f2p_total','p2p_passed','p2p_total'] if issue==29 else ['pr','transport','selection','status','exception','errno','f2p_count','p2p_count','container_removed','outcome_sha256']
        source_rows=data['rows'] if issue==29 else data['arms']
        rows=[{k:r[k] for k in keys if k in r} for r in source_rows]
        assert all(not isinstance(v,(dict,list)) for row in rows for v in row.values())
        stage(f'issue-{issue}-outcomes.json',dict(issue=issue,source_file=filename,source_sha256=hashlib.sha256(raw).hexdigest(),
            original_archive_sha256=data['archive_sha256'],rows=rows,model_calls=0,
            interpretation='Recorded outcomes only; no new task, regrading or solver evaluation. Raw archives remain protected locally.'))
    review=dict(public_eligible=True,approved_scope=SCOPE,
        scope='Whitelist projection of task/PR identifiers, categorical outcomes, scalar counts and provenance hashes from committed research reports.',
        excluded='No raw logs, source/test patches, test bodies, fixture data, model text, credentials or restricted archive contents.',
        retention='Original restricted bytes retained in protected local workspaces; public summary is not a full raw-evidence replacement.')
    (ROOT/'matchms-summary-public-review.json').write_text(json.dumps(review,indent=2)+'\n')
    stage('public-eligibility-review.json',review)
    manifest=dict(schema_version=1,issue=33,source_issues=[29,30,32],created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        visibility='public',bucket='open-athena/biotasks',retention='Retain while cited; no automatic deletion.',files=files,
        scope='Scalar Matchms follow-up outcomes and provenance; restricted raw archives excluded.')
    dest=ROOT/'matchms-summary-evidence-manifest.json';assert not dest.exists();dest.write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps({'objects':len(files)+1,'bytes':sum(r['bytes'] for r in files)}))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['prepare','publish']);p.add_argument('--worktrees',type=Path);a=p.parse_args()
    if a.action=='prepare':prepare(a.worktrees)
    else:publish('matchms-summary',SCOPE)
