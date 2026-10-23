"""Extract only frozen control task members; never regenerate or repair them."""
import hashlib
import json
from pathlib import Path, PurePosixPath
import tarfile

ROOT=Path(__file__).resolve().parent
MATCHMS=Path('/home/exedev/.local/share/biotasks/checkpoints/issue28-history-wide-20261022/biotasks28-history-matchms-matchms-001-results/phase-artifacts.tar.gz')


def main():
    plan=json.loads((ROOT/'control-plan.json').read_text())
    output=ROOT/'inputs-private/controls'
    rows=[]
    for repo in plan['repositories']:
        source=MATCHMS if repo['slug']=='matchms__matchms' else ROOT/'inputs-private'/f"{repo['slug']}-phase.tar.gz"
        with source.open('rb') as stream: assert hashlib.file_digest(stream,'sha256').hexdigest()==repo['original_phase']['sha256']
        expected={f['path']:f for task in repo['tasks'] for f in task['original_files']}
        found=set()
        with tarfile.open(source) as archive:
            for member in archive:
                if member.name not in expected:continue
                assert member.name not in found and member.isfile()
                parts=PurePosixPath(member.name).parts
                assert not member.name.startswith('/') and '..' not in parts
                spec=expected[member.name]
                assert member.size==spec['bytes'] and member.size<5*1024*1024
                raw=archive.extractfile(member).read()
                assert hashlib.sha256(raw).hexdigest()==spec['sha256']
                dest=output/member.name
                assert not any(p.is_symlink() for p in [dest,*dest.parents])
                dest.parent.mkdir(parents=True,exist_ok=True)
                if dest.exists():assert dest.read_bytes()==raw
                else:dest.write_bytes(raw)
                dest.chmod(int(spec['mode'],8))
                assert hashlib.sha256(dest.read_bytes()).hexdigest()==spec['sha256']
                found.add(member.name)
        assert found==set(expected)
        rows.append({'repo':repo['repo'],'source_phase_sha256':repo['original_phase']['sha256'],'task_names':[t['task'] for t in repo['tasks']],'files_verified':len(found),'bytes':sum(f['bytes'] for f in expected.values()),'task_file_changes':False})
    result={'scope':'Selected original task members extracted to ignored private durable workspace; no execution, regeneration or publication of raw Matchms content','repositories':rows,'files_verified':sum(r['files_verified'] for r in rows),'cleanup_condition':'Remove private extracted inputs after control evidence is durably archived or this investigation ends; original archives remain authoritative'}
    (ROOT/'control-input-readback.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'repos':len(rows),'files_verified':result['files_verified']}))

if __name__=='__main__':main()
