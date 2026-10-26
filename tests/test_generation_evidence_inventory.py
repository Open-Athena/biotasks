import hashlib
from pathlib import Path

import pytest

from biotasks.generation.finish_generation import verify_generation_source
from biotasks.validation.files import MAX_FILE, ValidationError, inventory


def test_native_history_evidence_can_exceed_small_input_count(tmp_path):
    source = tmp_path / 'generation-source'; source.mkdir()
    expected = []
    for n in range(1001):
        p = source / f'event-{n:04d}.json'; p.write_bytes(b'{}')
        expected.append({'path':p.name,'bytes':2,'mode':p.stat().st_mode & 0o777,'sha256':hashlib.sha256(b'{}').hexdigest()})
    rb={'source_members':expected}
    with pytest.raises(ValidationError, match='1000 files'): inventory(source)
    verify_generation_source(tmp_path, rb)
    (source/'event-0001.json').write_bytes(b'[]')
    with pytest.raises(ValidationError, match='lineage'): verify_generation_source(tmp_path, rb)


def test_evidence_verification_preserves_members_modes_and_byte_limits(tmp_path):
    source=tmp_path/'generation-source';source.mkdir();p=source/'event.json';p.write_bytes(b'{}')
    rb={'source_members':[{'path':p.name,'bytes':2,'mode':p.stat().st_mode & 0o777,'sha256':hashlib.sha256(b'{}').hexdigest()}]}
    verify_generation_source(tmp_path,rb)
    p.chmod(0o600)
    with pytest.raises(ValidationError,match='lineage'):verify_generation_source(tmp_path,rb)
    p.chmod(rb['source_members'][0]['mode']);(source/'extra.json').write_bytes(b'{}')
    with pytest.raises(ValidationError,match='lineage'):verify_generation_source(tmp_path,rb)
    (source/'extra.json').unlink();(source/'link').symlink_to(p)
    with pytest.raises(ValidationError,match='Symlinked'):verify_generation_source(tmp_path,rb)
    (source/'link').unlink()
    with p.open('wb') as stream: stream.truncate(MAX_FILE+1)
    with pytest.raises(ValidationError,match='byte bounds'):verify_generation_source(tmp_path,rb)
