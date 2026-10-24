"""Make an explicit, bounded public review for completed metadata/source evidence."""
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from common import sha,write
from preserve import inspect,verified_receipt


def main():
    verified_receipt(ROOT/'private/OHIF__Viewers')
    results=json.loads((ROOT/'results.json').read_text());assert results['cleanup_verified'] and results['anonymous_download_verified']
    files=[p for p in ROOT.iterdir() if p.is_file() and p.suffix in ['.py','.json','.md','.txt'] and p.name!='preserve.py' and not p.name.startswith(('final-evidence-','local-cleanup'))]
    files+=list((ROOT/'runs').rglob('*.json'))
    files+=[p for p in (ROOT/'private').glob('controller-*.log') if p.is_file()]
    files+=list((ROOT/'analysis').glob('*.py'))
    files.append(ROOT/'analysis/curation-preparation-note.json')
    rows=[]
    for path in sorted(set(files)):
        raw=path.read_bytes();inspect(raw)
        assert len(raw)<1024**2
        rows.append(dict(source=str(path.relative_to(ROOT)),path=str(path.relative_to(ROOT)),bytes=len(raw),sha256=sha(path)))
    assert sum(r['bytes'] for r in rows)<4*1024**2
    write(ROOT/'analysis/final-public-review.json',dict(schema_version=1,issue=39,public_eligible=True,cohort_sha256=sha(ROOT/'cohort.json'),
        source_results_sha256=sha(ROOT/'results.json'),scope='Completed frozen-export summary and source provenance',
        inputs=rows,source_review_sha256=sha(ROOT/'public-policy.json'),
        exclusions='No credentials, signed URLs, images/layers, installed dependencies, source checkout/data binaries or restricted Matchms material.',
        source_task_and_notices='Already separately preserved with verified anonymous input/runtime readback.',
        excluded_scanner_source=dict(path='preserve.py',sha256=sha(ROOT/'preserve.py'),source='https://github.com/Open-Athena/biotasks/blob/5e72a360/experiments/39-recorded-bootstrap/preserve.py',reason='Scanner guard literals are not execution logs; retain exact source in Git rather than weakening the raw artifact scanner.'),retention='Retain while cited; no automatic deletion.',model_calls=0))
    print(json.dumps(dict(reviewed_inputs=len(rows),reviewed_bytes=sum(r['bytes'] for r in rows))))


if __name__=='__main__':main()
