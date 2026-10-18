"""Map local snapshot manifests to prior publication receipts without bulk re-downloads."""
import datetime
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parent


def build():
    rows=[]
    for path in sorted(ROOT.glob('hf*snapshot-manifest.json')):
        assert path.stat().st_size<=16*1024**2
        raw=path.read_bytes();manifest=json.loads(raw);digest=hashlib.sha256(raw).hexdigest()
        receipt_path=path.with_name(path.name.replace('snapshot-manifest','upload-receipt'))
        row={'manifest':path.name,'manifest_sha256':digest,'stage':manifest.get('stage'),
             'receipt':receipt_path.name if receipt_path.exists() else None,
             'expected_objects':len(manifest.get('files',[]))+1,
             'expected_archive_members':sum(len(x.get('members',[])) for x in manifest.get('files',[]))}
        if not receipt_path.exists():
            row['status']='no_corresponding_receipt_requires_review'
        else:
            receipt=json.loads(receipt_path.read_text());expected=receipt.get('manifest_sha256',receipt.get('prefix','').rsplit('/',1)[-1])
            row.update(receipt_sha256=hashlib.sha256(receipt_path.read_bytes()).hexdigest(),bucket=receipt.get('bucket'),prefix=receipt.get('prefix'),
                       anonymous_download_verified=receipt.get('anonymous_download_verified'),verified_objects=receipt.get('verified_objects'),verified_archive_members=receipt.get('verified_archive_members'),
                       source_manifest_commit=receipt.get('source_manifest_commit',receipt.get('manifest_commit')),
                       receipt_status=receipt.get('status'))
            checks={'manifest_hash_matches':expected==digest,
                    'public_bucket':receipt.get('bucket')=='open-athena/biotasks' and receipt.get('visibility')=='public',
                    'anonymous_download_recorded':receipt.get('anonymous_download_verified') is True,
                    'object_count_matches':receipt.get('verified_objects')==row['expected_objects'],
                    'archive_member_count_matches':receipt.get('verified_archive_members')==row['expected_archive_members']}
            row['checks']=checks;row['status']='manifest_and_publication_receipt_match' if all(checks.values()) else 'receipt_or_manifest_requires_review'
        rows.append(row)
    # Resolve an explicitly recorded metadata-only replacement, retaining the failed original.
    by_digest={row['manifest_sha256']:row for row in rows}
    for path in sorted(ROOT.glob('hf*snapshot-manifest.json')):
        replacement=json.loads(path.read_text());correction=replacement.get('mode_metadata_correction',{})
        prior_digest=correction.get('supersedes_snapshot','').rsplit('/',1)[-1]
        if prior_digest not in by_digest:continue
        replacement_row=by_digest[hashlib.sha256(path.read_bytes()).hexdigest()]
        assert replacement_row['status']=='manifest_and_publication_receipt_match'
        original=by_digest[prior_digest];old=json.loads((ROOT/original['manifest']).read_text())
        a={x['path']:x for x in old['files']};b={x['path']:x for x in replacement['files']};assert set(a)==set(b)
        for name in a:
            assert (a[name]['bytes'],a[name]['sha256'])==(b[name]['bytes'],b[name]['sha256'])
            left={x['path']:x for x in a[name].get('members',[])};right={x['path']:x for x in b[name].get('members',[])};assert set(left)==set(right)
            for member in left:
                assert (left[member]['bytes'],left[member]['sha256'])==(right[member]['bytes'],right[member]['sha256'])
                assert int(left[member]['mode'],8)&0o7777==int(right[member]['mode'],8)
        assert correction['archive_bytes_unchanged'] is True
        original['status']='superseded_manifest_descriptor_error'
        original['superseded_by']={'manifest':replacement_row['manifest'],'prefix':replacement_row['prefix'],'receipt':replacement_row['receipt'],'proof':'Same object/member bytes and hashes; permission descriptors corrected by stripping type bits; replacement publication verified.'}
    return {'observed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'scope':'Local manifest-to-publication-receipt mapping; no fresh remote object download and no new independent source/mode-integrity claim.',
            'manifests':len(rows),'matched':sum(x['status']=='manifest_and_publication_receipt_match' for x in rows),
            'superseded_without_original_receipt':sum(x['status']=='superseded_manifest_descriptor_error' for x in rows),
            'requires_review':[x['manifest'] for x in rows if x['status'] not in ('manifest_and_publication_receipt_match','superseded_manifest_descriptor_error')],
            'snapshots':rows,'limitations':['Publication receipts establish their recorded verification event, not current remote object availability.','A snapshot faithfully preserving a failed/rejected source bundle does not establish task acceptance or release readiness.','Superseded or incomplete snapshots remain append-only; a later correction requires an explicit evidence link.']}


if __name__=='__main__':
    result=build();out=ROOT/'evidence/artifact-retention-reconciliation-20261018';out.mkdir(exist_ok=True)
    (out/'local-manifest-receipt-audit.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='snapshots'}))
