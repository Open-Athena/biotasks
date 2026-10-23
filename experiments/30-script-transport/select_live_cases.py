"""Freeze first recorded Matchms errno-7 case and known-success control before acquisition."""
import hashlib,json,tarfile
from pathlib import Path

ROOT=Path(__file__).resolve().parent
# Explicit external preserved original archive; do not copy raw content publicly.
ARCHIVE=Path('/home/exedev/.local/share/biotasks/checkpoints/issue28-history-wide-20261022/biotasks28-history-matchms-matchms-001-results/phase-artifacts.tar.gz')


def main():
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--assessment',required=True,type=Path);args=p.parse_args()
    assessment=json.loads(args.assessment.read_text())
    batches=assessment['coverage']['batches']
    failures=[(b['index'],e['pr']) for b in batches for e in b['validation_exceptions'] if e.get('errno')==7]
    first=min(failures)
    selected={first[1]:'first recorded errno-7 exception by batch index; no replacement on failure',671:'original exported success control; both reconstructed controls independently verified in issue29'}
    with ARCHIVE.open('rb') as f:archive_sha=hashlib.file_digest(f,'sha256').hexdigest()
    assert archive_sha==assessment['original_phase_sha256']
    found={}
    with tarfile.open(ARCHIVE) as tar:
        for member in tar:
            if not member.isfile() or not member.name.endswith('native-candidates.json'):continue
            assert member.size<1024**2
            raw=tar.extractfile(member).read()
            for pr in json.loads(raw):
                if pr['number'] in selected:
                    keep={k:pr[k] for k in ['number','base_sha','head_sha','url','changed_files']}
                    if pr['number'] in found:assert found[pr['number']]['identity']==keep
                    found[pr['number']]={'identity':keep,'reason':selected[pr['number']],'source_member':member.name,'source_member_sha256':hashlib.sha256(raw).hexdigest()}
    assert set(found)==set(selected)
    result={'repo':'matchms/matchms','cases':[found[n] for n in selected],'selection_frozen_before_diff_fetch':True,'assessment_sha256':hashlib.sha256(args.assessment.read_bytes()).hexdigest(),'original_phase_sha256':archive_sha,'original_failed_count':len(failures),'limits':['Original failed script/diff bytes were not retained; pinned refs will reconstruct inputs','No live transport or task recovery result yet','Do not replace selected failing case with easier one']}
    (ROOT/'live-cases.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'selected_prs':list(selected),'original_errno7_cases':len(failures)}))

if __name__=='__main__':main()
