"""Read original public #28 SAMtools make-test evidence; do not regrade it."""
import collections
import gzip
import hashlib
import json
from pathlib import Path
import re
import tarfile

ROOT=Path(__file__).resolve().parent
INPUT=ROOT/'samtools-native-log-input.json'
ARCHIVE=ROOT/'inputs-private/samtools-history-phase.tar.gz'

def sha(data):return hashlib.sha256(data).hexdigest()

def main():
    metadata=json.loads(INPUT.read_text())
    assert metadata['repo']=='samtools/samtools' and metadata['anonymous_download_verified']
    outer=metadata['archive'];assert outer['path']=='evidence/phase-artifacts.tar.gz'
    assert len(ARCHIVE.read_bytes())==outer['bytes'] and sha(ARCHIVE.read_bytes())==outer['sha256']
    name='native-observations/batch-0000/exec-0016-pr-None.json.gz'
    expected=metadata['member'];assert expected['path']==name
    with tarfile.open(ARCHIVE) as tar:
        member=tar.getmember(name);assert member.isfile() and member.size==expected['bytes']
        raw=tar.extractfile(member).read()
    assert sha(raw)==expected['sha256']
    record=json.loads(gzip.decompress(raw));command=record['command'];result=record['result']
    assert command=='export LD_LIBRARY_PATH=/usr/local/lib:$LD_LIBRARY_PATH && cd /workspace && make test'
    assert result['exit_code']==0
    stdout=result['stdout'];stderr=result['stderr']
    headings=collections.Counter(re.findall(r'^([A-Za-z_][A-Za-z0-9_]*):$',stdout,re.M))
    start=stdout.index('Number of tests:\n')
    summary=stdout[start:start+250]
    labels=['total','passed','failed','expected failure','unexpected pass']
    counts={}
    for label in labels:
        hits=re.findall(r'^\s*'+re.escape(label)+r'\s+\.\.\s+(\d+)\s*$',summary,re.M)
        assert len(hits)==1;counts[label]=int(hits[0])
    assert counts['total']==sum(counts[k] for k in labels if k!='total')
    assert headings['test_sort']==36 and sum(headings.values())==523 and counts['total']==1052
    report={'scope':'Original #28 bootstrap make-test output at recorded source ref; no PR validation, regrading or repair',
            'repo':metadata['repo'],'source_ref':metadata['ref'],'command_sha256':sha(command.encode()),
            'archive_sha256':outer['sha256'],'raw_member_path':name,'raw_member_sha256':expected['sha256'],
            'runner_exit_code':result['exit_code'],'duration_seconds':result['duration_sec'],
            'stdout_sha256':sha(stdout.encode()),'stderr_sha256':sha(stderr.encode()),
            'per_test_headings_total':sum(headings.values()),'unique_heading_names':len(headings),
            'repeated_heading_names':{k:v for k,v in sorted(headings.items()) if v>1},
            'perl_summary':counts,'make_components_after_perl_summary':bool(re.search(r'^test/merge/test_bam_translate',stdout[start:],re.M)),
            'model_calls':0,'limits':['Heading counts are not unique test identities','Perl summary counts do not alone cover subsequent C/shell components','This bootstrap source ref is not PR1605 head','Original successful run does not prove a candidate parser or generated task']}
    (ROOT/'samtools-native-log-audit.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ('repeated_heading_names','limits')}))
if __name__=='__main__':main()
