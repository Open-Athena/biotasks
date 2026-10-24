"""Bounded archive inspection and semantic validation of imported build evidence."""
import io
import json
from pathlib import Path
import re
import tarfile

from common import content_sha,native_prefix,safe,sha

MAX_EXPANDED=32*1024**2


def archive_records(path,kind):
    raw=path if isinstance(path,bytes) else Path(path).read_bytes();assert len(raw)<=MAX_EXPANDED
    if kind=='tar.zst':
        import zstandard
        with zstandard.ZstdDecompressor().stream_reader(io.BytesIO(raw)) as stream:
            expanded=stream.read(MAX_EXPANDED+1)
        assert len(expanded)<=MAX_EXPANDED
        handle=tarfile.open(fileobj=io.BytesIO(expanded),mode='r:')
    else:
        assert kind=='tar.gz';handle=tarfile.open(fileobj=io.BytesIO(raw),mode='r:gz')
    rows={};total=0
    with handle:
        for member in handle:
            name=str(safe(member.name))
            if member.isdir():continue
            assert member.isfile() and name not in rows and 0<=member.size<8*1024**2
            total+=member.size;assert total<=MAX_EXPANDED
            data=handle.extractfile(member).read();assert len(data)==member.size
            rows[name]=dict(data=data,mode=member.mode,bytes=member.size,sha256=content_sha(data))
    return rows


def verify_imported_failure(directory,prepared):
    directory=Path(directory)
    summary=json.loads((directory/'runtime-readback.json').read_text())
    output=directory/'runtime.tar.zst'
    assert sha(output)==summary['archive_sha256']
    outer=archive_records(output,'tar.zst')
    report=json.loads(outer['control-result.json']['data'])
    assert report['run_id']==summary['run_id']
    for name,digest in report['output_sha256'].items():assert outer[str(safe(name))]['sha256']==digest
    assert report['native_build_exit']==127 and report['scientific_stage']=='native_image_build_failed'
    assert report.get('controls_skipped') and 'controls_started' not in report and 'setup_exit' not in report
    assert not any(name.startswith('controls/') for name in outer)
    log=outer['first-build.log']['data'].decode()
    assert re.search(r'pnpm:\s*(?:command )?not found',log)
    command=re.search(r"The command '/bin/sh -c (.+)' returned a non-zero code:\s*127",log)
    assert command
    packed=archive_records(directory/'native-task.tar.gz','tar.gz')
    assert report['payload_sha256']['original-tasks.tar.gz']==sha(directory/'native-task.tar.gz')
    actual=archive_records(outer['control-artifacts.tar.gz']['data'],'tar.gz')
    for path,row in packed.items():
        assert actual[path]['sha256']==row['sha256'] and actual[path]['mode']==row['mode']
    dockerfiles=[(name,row) for name,row in packed.items() if name.endswith('/environment/Dockerfile')]
    assert len(dockerfiles)==1
    name,row=dockerfiles[0];task=name.split('/')[-3]
    assert (Path(prepared)/task/'environment/Dockerfile').read_bytes()==row['data']
    prefix,base=native_prefix(row['data'])
    effective=actual['infra/'+row['sha256']+'.Dockerfile']['data']
    label=('LABEL biotasks.run='+report['run_id']+'\n').encode()
    assert effective.count(label)==1 and effective.replace(label,b'',1)==row['data']
    assert ('RUN '+command[1]).encode() in prefix, 'Failure is not in shared native bootstrap prefix'
    build_rows=[json.loads(line) for line in outer['bounded-builds.jsonl']['data'].decode().splitlines()]
    assert len(build_rows)==1 and build_rows[0]['exit_code']==127
    assert build_rows[0]['dockerfile_sha256']==row['sha256']
    assert summary['different_worker_verified'] and summary['original_images_absent'] and summary['owned_resources_removed']
    assert report['cleanup']['verified_empty']
    return dict(kind='sealed_shared_prerequisite_stop',reference_run_id=report['run_id'],
        reference_archive_sha256=sha(output),bootstrap_prefix_sha256=content_sha(prefix),
        public_base_ref=base,recorded_base_repo_digests=summary['public_base_repo_digests'],
        measured_task=task,inner_exit_code=127,failed_run_command=command[1],
        measured_control_pairs=0,policy='Not attempted under prior verified prerequisite-failure stop; no new measured failure or score')
