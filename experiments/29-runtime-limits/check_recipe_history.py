"""Bind saved RUN commands to original observations; do not execute recipes."""
import hashlib
import json
from pathlib import Path
import re
import tarfile

ROOT=Path(__file__).resolve().parent


def main():
    rows=[]
    for slug in ['OHIF__Viewers','scverse__scanpy']:
        path=ROOT/'inputs-private'/f'{slug}-phase.tar.gz'
        with tarfile.open(path) as archive:
            member=next(m for m in archive if m.name.endswith('transcript.jsonl'))
            raw=archive.extractfile(member).read()
        turns=[json.loads(line) for line in raw.splitlines()]
        boot=json.loads((ROOT/'inputs-private'/f'{slug}-bootstrap.json').read_text())
        commands=[line[4:] for line in boot['dockerfile_reconstruction'].splitlines() if line.startswith('RUN ')]
        bash=[t for t in turns if t['action']=='BASH']
        assert len(commands)==len(bash)
        failures=[]
        for command,turn in zip(commands,bash,strict=True):
            assert command==turn['input'], 'Multiline or reordered command requires explicit handling'
            match=re.match(r'exit=(-?\d+)\n',turn['observation']); assert match
            status=int(match[1])
            if status:
                failures.append({'step':turn['step'],'command_sha256':hashlib.sha256(command.encode()).hexdigest(),'original_exit':status,'command':command,'externally_managed_environment':'externally-managed-environment' in turn['observation']})
        rows.append({'repo':slug,'archive_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'transcript_member':member.name,'transcript_sha256':hashlib.sha256(raw).hexdigest(),'bash_commands':len(bash),'recipe_commands_match_transcript':True,'nonzero_commands_retained':failures,'limits':'Original observations, not fresh Docker replay. Zero shell status can mask failures in piped commands.'})
    result={'scope':'Read-only original recipe/transcript comparison, no build or model calls','repositories':rows,'conclusion':'Scanpy saved Dockerfile retains original exit-1 pip command; syntax-only preflight does not establish executable reconstruction. OHIF has no nonzero BASH observations but unpinned dependencies/pipeline status masking remain.'}
    (ROOT/'recipe-history-results.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'repos':len(rows),'retained_nonzero_commands':sum(len(r['nonzero_commands_retained']) for r in rows)}))

if __name__=='__main__':main()
