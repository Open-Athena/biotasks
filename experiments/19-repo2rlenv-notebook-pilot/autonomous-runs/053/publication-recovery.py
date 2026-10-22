import json,shutil
from pathlib import Path
from publish_scientific_release import SerialHfApi,publication_target
from repo2rlenv.campaigns.release import recover_empty_upload,verify_release
stage=Path('/tmp/biotasks19-mdanalysis053-release-staged');receipt=Path('/tmp/biotasks19-mdanalysis053-publication.json');original=Path('/tmp/biotasks19-mdanalysis053-publication-original-dispatch.json');assert not original.exists()
files=verify_release(stage);api=SerialHfApi();head,obsolete=publication_target(api,files['repo_id'],files);assert head and not obsolete
remote=set(api.list_repo_files(files['repo_id'],repo_type='dataset',revision=head));assert remote<= {'.gitattributes'}
shutil.copyfile(receipt,original)
print(json.dumps({'remote_empty_verified':True,'original_dispatch_preserved':True,'owned_public_destination':files['repo_id']}),flush=True)
result=recover_empty_upload(stage,api=api,receipt=receipt,batch_size=16)
print(json.dumps(result))
