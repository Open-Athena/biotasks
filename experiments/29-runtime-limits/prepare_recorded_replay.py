"""Bind retained executable actions and original outcomes without editing inputs."""
import hashlib,json,re,tarfile
from pathlib import Path
ROOT=Path(__file__).resolve().parent


def sha(data):return hashlib.sha256(data).hexdigest()


def main():
    cases=[('scanpy',ROOT/'inputs-private/scverse__scanpy-phase.tar.gz'),
           ('ohif',ROOT/'inputs-private/OHIF__Viewers-phase.tar.gz'),
           ('macs',ROOT.parents[2]/'31/experiments/31-historical-builds/inputs-private/original-phase.tar.gz')]
    public=[]
    for name,path in cases:
        with path.open('rb') as stream:archive_sha=hashlib.file_digest(stream,'sha256').hexdigest()
        with tarfile.open(path,'r:gz') as archive:
            transcripts=[m for m in archive if m.isfile() and m.name.startswith('bootstrap/') and m.name.endswith('/transcript.jsonl')]
            assert len(transcripts)==1
            member=transcripts[0];raw=archive.extractfile(member).read()
            boot_member=member.name.rsplit('/',1)[0]+'/bootstrap.json'
            boot_raw=archive.extractfile(boot_member).read();boot=json.loads(boot_raw)
        turns=[json.loads(line) for line in raw.splitlines()]
        assert [t['step'] for t in turns]==sorted(t['step'] for t in turns)
        assert set(t['action'] for t in turns)<={'BASH','INVALID'}
        actions=[]
        for turn in turns:
            if turn['action']=='INVALID':continue  # No upstream shell execution for INVALID.
            match=re.match(r'^exit=(\d+)\n',turn['observation']);assert match
            actions.append({'step':turn['step'],'command':turn['input'],'command_sha256':sha(turn['input'].encode()),
                            'expected_exit_code':int(match[1]),'original_observation_sha256':sha(turn['observation'].encode()),'timeout_seconds':300})
        assert all(a['expected_exit_code']!=124 for a in actions),'Original command timeout needs separate cancellation accounting'
        base=re.search(r'^FROM (.+)$',boot['dockerfile_reconstruction'],re.M)[1]
        # Regenerate upstream's reconstruction exactly: prove which actions it saved.
        generated='\n'.join(['# Auto-generated from r2e-bootstrap agent transcript.',
            '# Build from the cloned repo root: `docker build -t my-image .`',f'FROM {base}','WORKDIR /workspace','COPY . /workspace','']+
            ['RUN '+a['command'].replace('\n',' \\\n    ') for a in actions]+[''])
        assert generated==boot['dockerfile_reconstruction']
        payload={'repo':boot['repo'],'ref':boot['ref'],'base_image':base,'actions':actions,
                 'test_cmds':boot['test_cmds'],'rebuild_cmds':boot['rebuild_cmds'],
                 'original_smoke_passed':boot['smoke_passed'],'original_verify_passed':boot['verify_passed']}
        dest=ROOT/'inputs-private'/f'{name}-recorded-replay.json';dest.write_text(json.dumps(payload,indent=2)+'\n');dest.chmod(0o600)
        public.append({'case':name,'repo':boot['repo'],'ref':boot['ref'],'base_image':base,
                       'archive_sha256':archive_sha,'transcript_member':member.name,'transcript_sha256':sha(raw),
                       'bootstrap_member_sha256':sha(boot_raw),'payload_sha256':sha(dest.read_bytes()),
                       'actions':[{k:v for k,v in action.items() if k!='command'} for action in actions],
                       'invalid_actions_without_execution':sum(t['action']=='INVALID' for t in turns),
                       'saved_dockerfile_exactly_regenerated':True,
                       'original_smoke_passed':boot['smoke_passed'],'original_verify_passed':boot['verify_passed']})
    report={'scope':'Retained-command inventory only; no replay execution or command edits',
            'cases':public,'model_calls':0,'limits':['Identical commands/outcome codes do not guarantee identical filesystem or dependency versions',
                'Replay must use original bash login-shell execution and full checkout copy, not Dockerfile RUN semantics',
                'Unexpected exit codes or timeouts must stop the frozen replay; no repair or retry loop']}
    (ROOT/'recorded-replay-manifest.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps([{'case':r['case'],'bash_actions':len(r['actions']),'nonzero_steps':[a['step'] for a in r['actions'] if a['expected_exit_code']],'original_smoke_passed':r['original_smoke_passed'],'original_verify_passed':r['original_verify_passed']} for r in public]))


if __name__=='__main__':main()
