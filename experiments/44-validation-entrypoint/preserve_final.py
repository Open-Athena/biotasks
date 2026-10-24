"""Archive the bounded public metadata allowlist; native bytes have six snapshots."""
import argparse
from pathlib import Path
import shutil

from biotasks.validation import preservation
from biotasks.validation.archives import pack
from biotasks.validation.files import inventory, read_json, sha, write_json

ROOT=Path(__file__).resolve().parent
NAMES=['logbook.md','results.md','execution-plan.json','execution-plan-recovery.json','reference-inputs.json','native-manifest.json','recovery-manifest.json','pre-admission-checkpoint.json','recovery-pre-admission.json','native-started.json','final-accounting.json','post-native-budget-guard.json','bridge-profile-check.json','native-comparison.json','recovery-comparison.json','prepare_reference.py','analyse_native.py','run_native.sh','run_recovery.sh','local-scratch-cleanup.json','github/pr-46-final-published.json','github/pr-validation-body-final.md']
DIRECTORY=ROOT/'inputs-private/final-evidence'
POLICY={'eligible':True,'review':'Own source, manifests, accounting, synthetic/default check logs and reference comparison metadata only. Native task/log bytes remain in the six separately reviewed anonymous-readback snapshots. No credentials, images, environments, biological datasets or withheld Matchms material.'}


def main():
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=['prepare','publish']);args=parser.parse_args()
    archive=read_json(ROOT/'native-manifest.json')['archive']
    if args.action=='prepare':
        selected=list(NAMES)
        selected += [p.relative_to(ROOT).as_posix() for p in (ROOT/'local-checks').rglob('*.txt')]
        selected += [p.relative_to(ROOT).as_posix() for p in (ROOT/'runs').rglob('*.json')]
        staged=DIRECTORY/'tree'
        if staged.exists():shutil.rmtree(staged)
        staged.mkdir(parents=True)
        for name in selected:
            source=ROOT/name;dest=staged/name
            dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,dest)
            assert sha(source)==sha(dest)
        license=ROOT.parents[1]/'LICENSE'
        shutil.copyfile(license,staged/'LICENSE')
        bundle=DIRECTORY/'evidence.tar.gz'
        bundle.unlink(missing_ok=True)
        package=pack(staged,bundle)
        for name,row in [('evidence.tar.gz',package)]:preservation.inspect((DIRECTORY/name).read_bytes(),name)
        manifest=preservation.prepare(DIRECTORY,{'evidence.tar.gz':bundle},{'issue':44,'purpose':'Final source/check/accounting metadata; existing-export validation only','pipeline_pr':'https://github.com/Open-Athena/biotasks/pull/46','pipeline_head':'1f6e7fe22e5c536a516eeef1aba105a59bfe944f','native_runtime_commit':'92afd3e4','budget_guard_verified_offline':True,'installed_bridge_verified_offline_and_local_sdk_profile':True,'scientific_checkpoint':'42be192b','native_model_calls':0,'native_metadata_members':package['files'],'public_policy':POLICY,'retention':'Retain while cited; no automatic deletion'})
        write_json(ROOT/'final-evidence-manifest.json',manifest)
        assert sha(ROOT/'final-evidence-manifest.json')==sha(DIRECTORY/'preserved/manifest.json')
        print(dict(prepared=True,members=len(package['files']),bundle_bytes=bundle.stat().st_size,manifest_sha256=sha(ROOT/'final-evidence-manifest.json')))
    else:
        assert sha(ROOT/'final-evidence-manifest.json')==sha(DIRECTORY/'preserved/manifest.json')
        receipt=preservation.publish(DIRECTORY,archive,POLICY)
        preservation.verify_receipt(DIRECTORY)
        write_json(ROOT/'final-hf-receipt.json',receipt)
        print(dict(anonymous_download_verified=receipt['anonymous_download_verified'],prefix=receipt['prefix'],objects=len(receipt['objects'])))


if __name__=='__main__':main()
