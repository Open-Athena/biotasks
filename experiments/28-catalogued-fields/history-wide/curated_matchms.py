"""Approved public evidence selection, with independently checked local originals.

This operates on archival copies only. It never runs or edits generated tasks.
"""

import datetime
import gzip
import hashlib
import io
import json
from pathlib import Path
import re
import subprocess
import tarfile
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parent
BASE = ROOT.parent
SLUG = 'matchms__matchms'
RUN = 'biotasks28-history-matchms-matchms-001'
KIND = 'curated_public_with_local_originals'
STAGE = 'matchms-curated-public'
BUCKET = 'open-athena/biotasks'
ORIGINAL_MANIFEST = ROOT / 'archives/drafts/matchms__matchms-unpublished-private-manifest.json'
ORIGINAL_REVIEW = ROOT / 'publication-reviews/history/matchms__matchms-private-unpublished.json'
LOCAL_RECEIPT = ROOT / 'archives/matchms__matchms-local-originals-receipt.json'
RECETOX = 'https://www.recetox.muni.cz/en/services/recetox-central-laboratories/biomarker-analysis-laboratories/recetox-mass-spectrum-reference-library'
CC = 'https://creativecommons.org/licenses/by-nc/4.0/'


def read(path):
    return json.loads(path.read_text())


def encoded(value):
    return (json.dumps(value, indent=2) + '\n').encode()


def sha(path):
    with path.open('rb') as source:
        return hashlib.file_digest(source, 'sha256').hexdigest()


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def original_sources(state):
    review = read(ORIGINAL_REVIEW)
    source = state / (RUN + '-results')
    sources = {'evidence/' + n: source / n for n in review['reviewed_files']}
    sources.update({'public-eligibility-review.json': ORIGINAL_REVIEW,
        'native-config.json': ROOT / 'native-configs' / (SLUG + '.json'),
        'history-protocol.md': ROOT / 'execution-protocol.md',
        'reference-payload-manifest.json': ROOT / 'payload-manifest.json',
        'candidate-identities.json': ROOT / 'candidate-identities' / (SLUG + '.json'),
        'submission-provenance.json': ROOT / 'submission-provenance' / (SLUG + '.json'),
        'restricted-retention-addendum.md': ROOT / 'restricted-retention-addendum.md',
        'source-data-review.json': ROOT / 'publication-reviews' / (SLUG + '-data-review.json'),
        'private-bucket-visibility-proof.json': ROOT / 'restricted-retention-bucket.json'})
    sources.update({'source-notices/' + p.name: p for p in (BASE / 'preflight/licenses').glob(SLUG + '--*')})
    sources.update({'source-notices/history/' + n: ROOT / 'source-notices' / n
        for n in review['additional_source_notices']})
    sources['source-notices/Repo2RLEnv-LICENSE'] = BASE / 'preflight/licenses/huggingface__Repo2RLEnv--LICENSE'
    return sources


def original_inventory(state):
    """Actual original files plus every original tar member; no receipt-only waiver."""
    from archive_result import baseline
    assert state.is_absolute() and state.stat().st_mode & 0o077 == 0
    manifest = read(ORIGINAL_MANIFEST)
    sources = original_sources(state)
    assert set(sources) == {r['path'] for r in manifest['files']}
    rows = []
    for item in manifest['files']:
        path = sources[item['path']]
        assert path.is_file() and not path.is_symlink()
        assert path.stat().st_size == item['bytes'] and sha(path) == item['sha256'], item['path']
        rows.append({'object': item['path'], 'local_path': str(path.resolve()),
            'bytes': item['bytes'], 'sha256': item['sha256']})
        if item['path'] == 'evidence/phase-artifacts.tar.gz':
            assert baseline.members(path) == item['members']
    return {'schema': 1, 'retention': 'User-approved protected local originals; retain while referenced. No automatic deletion.',
        'original_source_manifest_sha256': sha(ORIGINAL_MANIFEST), 'objects': rows,
        'original_phase_members': next(r['members'] for r in manifest['files'] if r['path'] == 'evidence/phase-artifacts.tar.gz')}


def verify_local_originals(state, manifest=None):
    private = state / 'matchms-local-original-retention.json'
    actual = original_inventory(state)
    assert read(private) == actual, 'Local original inventory changed'
    receipt = read(LOCAL_RECEIPT)
    assert receipt['local_original_manifest_sha256'] == sha(private)
    phase = next(r for r in actual['objects'] if r['object'] == 'evidence/phase-artifacts.tar.gz')
    assert receipt['original_phase_sha256'] == phase['sha256']
    assert receipt['original_objects_verified'] == len(actual['objects'])
    assert receipt['original_phase_members_verified'] == len(actual['original_phase_members'])
    if manifest is not None:
        assert manifest['archive_kind'] == KIND
        assert manifest['local_originals_receipt_sha256'] == sha(LOCAL_RECEIPT)
        assert manifest['original_phase_sha256'] == phase['sha256']
        assert manifest['local_original_manifest_sha256'] == sha(private)
        assert manifest['original_source_manifest_sha256'] == sha(ORIGINAL_MANIFEST)
    return receipt


def allow_member(name):
    """Only these exact metadata/code classes are eligible; all other bytes stay local."""
    path = Path(name)
    assert not path.is_absolute() and '..' not in path.parts
    parts = path.parts
    if (len(parts) == 5 and parts[:2] == ('outputs', SLUG)
            and re.fullmatch(SLUG + r'-\d+', parts[2]) and parts[3] == 'tests'
            and path.name in ['f2p.json', 'p2p.json', 'verifier.py']):
        return 'Apache-2.0', 'Matchms test identifiers / pinned Repo2RLEnv verifier code; original software notices retained.'
    if (len(parts) == 6 and parts[:2] == ('jobs', 'fresh')
            and re.fullmatch(SLUG + r'-\d+-(?:nop|oracle)', parts[2]) and parts[-2] == 'verifier'
            and path.name in ['reward.txt', 'reward-details.json']):
        return 'Apache-2.0', 'Original execution-derived reward/test-identifier metadata; no raw test-output or patch bytes.'
    if (len(parts) == 3 and parts[0] == 'native-observations' and re.fullmatch(r'batch-\d{4}', parts[1])
            and (path.name == 'billing.json' or re.fullmatch(r'cost-quote-\d{3}\.json', path.name))):
        return 'Apache-2.0', 'Original request-cost/price metadata; no request body, response text or patch-bearing command.'
    if name == 'infra/history-identities.json':
        return 'Apache-2.0', 'Original PR-number inventory; factual execution metadata.'
    return None


def public_sources(state):
    stage = state / STAGE
    return {'evidence/curated-phase-artifacts.tar.gz': stage / 'curated-phase-artifacts.tar.gz',
        **{name: stage / name for name in ['README.md', 'file-licenses.json', 'original-member-disposition.json']},
        'local-originals-receipt.json': LOCAL_RECEIPT,
        'public-eligibility-review.json': ROOT / 'publication-reviews' / (SLUG + '.json'),
        'retention-addendum.md': ROOT / 'public-retention-addendum-20261023.md',
        **{name: ROOT / relative for name, relative in {
            'assessment.json': 'results/matchms__matchms.json',
            'terminal-bindings.json': 'results/matchms__matchms-terminal-bindings.json',
            'runtime-equivalence.json': 'results/matchms__matchms-full-runtime-equivalence.json',
            'control-data-crossref.json': 'task-reviews/matchms__matchms-control-data-crossref.json',
            'candidate-identities.json': 'candidate-identities/matchms__matchms.json',
            'native-config.json': 'native-configs/matchms__matchms.json',
            'history-protocol.md': 'execution-protocol.md',
            'source-notices/validation-ref-proof.json': 'source-notices/matchms__matchms/terminal-notice-proof-20261023.json',
        }.items()},
        'source-notices/Matchms-Apache-2.0.txt': BASE / 'preflight/licenses/matchms__matchms--LICENSE',
        'source-notices/Repo2RLEnv-Apache-2.0.txt': BASE / 'preflight/licenses/huggingface__Repo2RLEnv--LICENSE',
        'source-notices/BioTasks-Apache-2.0.txt': ROOT.parents[2] / 'LICENSE'}


def prepare(state):
    from archive_result import baseline
    stage = state / STAGE
    stage.mkdir(mode=0o700, exist_ok=False)
    actual = original_inventory(state)
    private = state / 'matchms-local-original-retention.json'
    assert not private.exists()
    private.write_bytes(encoded(actual)); private.chmod(0o600)
    phase = next(r for r in actual['objects'] if r['object'] == 'evidence/phase-artifacts.tar.gz')
    local = {'approved_disposition': KIND, 'local_originals_verified': True,
        'verified_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'local_original_manifest_sha256': sha(private), 'original_source_manifest_sha256': sha(ORIGINAL_MANIFEST),
        'original_phase_sha256': phase['sha256'], 'original_objects_verified': len(actual['objects']),
        'original_phase_members_verified': len(actual['original_phase_members']),
        'storage': 'Protected persistent VM checkpoint, outside /tmp; not an HF original archive.',
        'retention': 'Retain while referenced; no automatic deletion.',
        'limitation': 'VM-local originals are not independently downloadable from the public curated snapshot.'}
    LOCAL_RECEIPT.write_bytes(encoded(local))
    selected, licenses, inventory = {}, {}, []
    with tarfile.open(Path(phase['local_path']), 'r|gz') as archive:
        for member in archive:
            if not member.isfile():
                continue
            assert member.size < 16 * 1024**2
            raw = archive.extractfile(member).read()
            decision = allow_member(member.name)
            row = {'path': member.name, 'bytes': member.size, 'mode': oct(member.mode & 0o7777), 'sha256': digest(raw),
                'disposition': 'published_verbatim' if decision else 'local_original_only',
                'source': 'https://github.com/matchms/matchms'}
            match = re.search(r'(?:matchms__matchms-|pr-)(\d+)', member.name)
            if match:
                row['source'] += '/pull/' + match.group(1)
            if decision:
                selected[member.name] = (raw, member.mode & 0o7777)
                licenses[member.name] = {'terms': decision[0], 'basis': decision[1], 'source': row['source'],
                    'source_member_sha256': row['sha256'], 'changes': 'None; exact original member bytes.'}
            else:
                row['reason'] = 'Outside explicit metadata/code allowlist; may embed repeated unresolved fixture/patch/log content. No finding that every omitted file is restricted.'
            inventory.append(row)
    assert len(inventory) == len(actual['original_phase_members']) == 4190
    assert [{k: row[k] for k in ['path', 'bytes', 'mode', 'sha256']} for row in inventory] == actual['original_phase_members']
    review = read(state / 'matchms-spectral-fixture-review.json')
    recetox = [r for r in review['spectral_fixture_patch_sections'] if r['task'] in ['matchms__matchms-194', 'matchms__matchms-195']]
    assert len(recetox) == 2 and recetox[0]['section_sha256'] == recetox[1]['section_sha256']
    raw = recetox[0]['section_excerpt'].encode()
    assert digest(raw) == recetox[0]['section_sha256'] and len(raw) == recetox[0]['section_bytes']
    key = 'third-party-data/recetox-perylene-pr194-195.patch'
    selected[key] = (raw, 0o644)
    licenses[key] = {'terms': 'CC BY-NC (fixture unversioned; provider links CC BY-NC 4.0)',
        'creator': 'Price et al., RECETOX, Masaryk University (CZ)',
        'source': RECETOX, 'license_url': CC,
        'source_prs': ['https://github.com/matchms/matchms/pull/194', 'https://github.com/matchms/matchms/pull/195'],
        'source_section_sha256': digest(raw),
        'changes': 'Complete patch section extracted verbatim from original tests/test.sh; no spectrum values changed.',
        'purpose': 'Noncommercial research-evidence publication; retain attribution and applicable terms.'}
    # Make omissions mechanically inspectable, including encoded PR110 records.
    assert all(not allow_member(r['path']) for r in inventory if r['disposition'] == 'local_original_only')
    for fixture in review['spectral_fixture_patch_sections']:
        if fixture not in recetox:
            withheld = fixture['section_excerpt'].encode()
            assert all(withheld not in data for data, _ in selected.values())
    target = stage / 'curated-phase-artifacts.tar.gz'
    with target.open('wb') as sink, gzip.GzipFile(fileobj=sink, mode='wb', filename='', mtime=0) as zipped, tarfile.open(fileobj=zipped, mode='w|') as archive:
        for name, (data, mode) in sorted(selected.items()):
            assert not baseline.SECRET.search(data)
            member = tarfile.TarInfo(name); member.size = len(data); member.mode = mode
            archive.addfile(member, io.BytesIO(data))
    (stage / 'original-member-disposition.json').write_bytes(encoded({'original_phase_sha256': phase['sha256'],
        'original_members': len(inventory), 'members': inventory,
        'local_originals_receipt_sha256': sha(LOCAL_RECEIPT), 'scope': 'Hashes and source links are not a substitute for original bytes; untouched originals retained locally.'}))
    (stage / 'file-licenses.json').write_bytes(encoded({'scope': 'Per-member terms; no blanket Apache license for the archive or third-party spectrum data.',
        'members': licenses, 'metadata_and_analysis': 'BioTasks Apache-2.0; upstream notices retained.',
        'third_party_notice': 'Third-party materials remain under their respective licenses; no additional rights are granted.'}))
    (stage / 'README.md').write_text('''# Matchms research evidence

This is a curated public evidence snapshot, not the complete original phase or a runnable task release. Original tasks, logs, patches and grades were not changed or rerun. The original 4,190-member phase and all original reviewed objects are retained unchanged in protected persistent VM storage, verified by the local-originals receipt. Public-only replay is incomplete for omitted records; local retention depends on the VM storage.

The original-member disposition manifest lists every path, hash, source and inclusion/omission. The archive includes original test identifiers, verifier code, reward/charge metadata and one explicitly attributed reference-spectrum patch. Raw command/diff/transcript/test-output records outside this allowlist stay local because they may repeat unresolved fixtures. This conservative omission is not a claim that every omitted file has restrictive terms.

The RECETOX Perylene fixture is attributed to Price et al., RECETOX, Masaryk University (CZ), and was extracted unchanged from Matchms PR194/195. Its original LICENSE field says CC BY-NC without a version; the RECETOX provider page links CC BY-NC 4.0. Preserve the author/license metadata, source/provider links and noncommercial condition. Extraction of the patch section is the only packaging change; no peak values were changed. This snapshot is published for noncommercial research evidence.

Third-party materials remain under their respective licenses; no additional rights are granted. See file-licenses.json and source-notices/. In particular, the software Apache-2.0 notices do not relicense the RECETOX data. Other observed/reference spectra with unresolved terms remain local; no permission is inferred for commercial use, training, dependency/base-image data or omitted fixtures.

RECETOX source: ''' + RECETOX + '\n\nLicense linked by provider: ' + CC + '\n')
    sources = public_sources(state)
    license_document = read(stage / 'file-licenses.json')
    object_terms = {}
    for name, path in sources.items():
        object_terms[name] = {'terms': 'Apache-2.0',
            'basis': 'BioTasks research metadata/analysis or attributed software notice; no spectrum payload.',
            'source_sha256': sha(path) if name != 'file-licenses.json' else None}
    object_terms['evidence/curated-phase-artifacts.tar.gz'] = {
        'terms': 'Mixed; see exact member entries below. Apache-2.0 does not cover RECETOX spectrum data.',
        'original_phase_sha256': phase['sha256'], 'changes': 'Explicit original-member selection plus one verbatim extracted fixture patch.'}
    license_document['objects'] = object_terms
    license_document['objects']['file-licenses.json']['basis'] = 'Generated provenance/terms manifest; its own integrity hash is in manifest.json.'
    (stage / 'file-licenses.json').write_bytes(encoded(license_document))
    files = []
    for name, path in sources.items():
        assert path.is_file() and path.stat().st_size < 16 * 1024**2
        row = {'path': name, 'bytes': path.stat().st_size, 'sha256': sha(path)}
        if name.endswith('.tar.gz'):
            row.update(archive_format='tar.gz', members=baseline.members(path, scan=True))
        else:
            assert not baseline.SECRET.search(path.read_bytes())
        files.append(row)
    manifest = {'issue': 28, 'repo': 'matchms/matchms', 'ref': read(ORIGINAL_MANIFEST)['ref'],
        'archive_kind': KIND, 'archive_bucket': BUCKET, 'archive_visibility': 'public',
        'created_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'publication_checkpoint': subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
        'archive_client_resource_profile_sha256': sha(ROOT / 'archive-client-profile.json'),
        'original_phase_sha256': phase['sha256'], 'original_source_manifest_sha256': sha(ORIGINAL_MANIFEST),
        'local_originals_receipt_sha256': sha(LOCAL_RECEIPT), 'local_original_manifest_sha256': sha(private),
        'retention': 'Public curated evidence and protected local originals retained while referenced; no automatic deletion.',
        'full_original_phase_uploaded': False, 'files': files}
    path = ROOT / 'archives' / (SLUG + '-manifest.json')
    assert not path.exists(); path.write_bytes(encoded(manifest))
    verify_local_originals(state, manifest)
    print(json.dumps({'curated_members': len(selected), 'original_members': len(inventory),
        'original_members_published_verbatim': sum(r['disposition'] == 'published_verbatim' for r in inventory),
        'public_objects': len(files) + 1, 'originals_unchanged_and_locally_verified': True}))


def publish(state, *, verify_only=False):
    from archive_result import baseline
    from huggingface_hub import HfApi
    from huggingface_hub.utils import disable_progress_bars
    from retention import verified_receipt
    disable_progress_bars()
    path = ROOT / 'archives' / (SLUG + '-manifest.json')
    manifest = read(path); verify_local_originals(state, manifest)
    subprocess.run(['git', 'diff', '--exit-code', '--', str(path)], capture_output=True, check=True)
    subprocess.run(['git', 'ls-files', '--error-unmatch', str(path)], capture_output=True, check=True)
    objects = {'manifest.json': path, **public_sources(state)}
    for name, source in objects.items():
        if name != 'manifest.json':
            original = next(r for r in manifest['files'] if r['path'] == name)
            assert source.stat().st_size == original['bytes'] and sha(source) == original['sha256']
    prefix = 'research/28-catalogued-fields/' + manifest['created_utc'][:10] + '/' + sha(path)
    api = HfApi(); prior = list(api.list_bucket_tree(BUCKET, prefix=prefix, recursive=True))
    known = {r.path for r in prior if r.type == 'file'}
    assert known <= {prefix + '/' + name for name in objects}
    attempt = state / (RUN + '-curated-publication-attempt.json')
    if verify_only:
        assert known == {prefix + '/' + name for name in objects}
    elif prior:
        assert read(attempt)['prefix'] == prefix
    else:
        attempt.write_bytes(encoded({'prefix': prefix, 'manifest_sha256': sha(path)}))
    missing = [(str(source), prefix + '/' + name) for name, source in objects.items() if prefix + '/' + name not in known]
    if missing:
        assert not verify_only
        api.batch_bucket_files(BUCKET, add=missing)
    listing = {r.path: r for r in api.list_bucket_tree(BUCKET, prefix=prefix, recursive=True) if r.type == 'file'}
    assert set(listing) == {prefix + '/' + name for name in objects}
    with TemporaryDirectory(prefix='matchms-curated-readback-', dir=state) as temporary:
        downloads = []
        for name in objects:
            dest = Path(temporary) / name; dest.parent.mkdir(parents=True, exist_ok=True)
            downloads.append((listing[prefix + '/' + name], dest))
        api.download_bucket_files(BUCKET, downloads, raise_on_missing_files=True, token=False)
        for name, source in objects.items():
            dest = Path(temporary) / name
            assert dest.stat().st_size == source.stat().st_size and sha(dest) == sha(source)
            if name.endswith('.tar.gz'):
                assert baseline.members(dest) == next(r['members'] for r in manifest['files'] if r['path'] == name)
    local = verify_local_originals(state, manifest)
    receipt = {'verified_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'bucket': BUCKET,
        'prefix': prefix, 'manifest_sha256': sha(path), 'archive_kind': KIND, 'visibility': 'public',
        'anonymous_download_verified': True, 'curated_public_bytes_verified': True,
        'local_originals_verified': True, 'local_originals_receipt_sha256': sha(LOCAL_RECEIPT),
        'original_phase_sha256': local['original_phase_sha256'],
        'local_original_manifest_sha256': local['local_original_manifest_sha256'],
        'full_original_phase_uploaded': False, 'verified_objects': len(objects),
        'verified_archive_members': sum(len(r.get('members', [])) for r in manifest['files']),
        'original_phase_members_verified_locally': local['original_phase_members_verified'],
        'temporary_readbacks_removed': True, 'overwrites': False,
        'read_only_fresh_verification': verify_only, 'verification_source_sha256': sha(Path(__file__)),
        'retention': manifest['retention']}
    assert verified_receipt(receipt, manifest)
    suffix = '-fresh-readback.json' if verify_only else '-receipt.json'
    (ROOT / 'archives' / (SLUG + suffix)).write_bytes(encoded(receipt))
    print(json.dumps(receipt, indent=2))


def run(action, state):
    assert action in ['prepare', 'publish', 'verify']
    prepare(state) if action == 'prepare' else publish(state, verify_only=action == 'verify')
