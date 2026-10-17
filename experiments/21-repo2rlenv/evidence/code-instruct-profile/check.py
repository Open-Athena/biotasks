import hashlib,json
from pathlib import Path
from repo2rlenv.pipelines._oss_instruct import detect_repo_package
root=Path('/tmp/biotasks21-private/lcc-control-preparation/original/environment/source')
detected=detect_repo_package(root,'biopython')
record={'stage':'native_package_detection_only','repository':'biopython/biopython','revision':'4eda92397bdedff82f04ac218a862ae25ebdc4a8','native_detected_package':detected,'expected_import_package':'Bio','expected_package_init_present':(root/'Bio/__init__.py').is_file(),'pyproject_sha256':hashlib.sha256((root/'pyproject.toml').read_bytes()).hexdigest(),'generation_executed':False,'model_calls':0,'native_candidate_limit_for_target_three':15,'approved_candidate_cap':10,'required_adaptations':['explicit package mapping Bio before authoring','enforce 10 candidate cap independently of output target'],'source_basis':['pipelines/_oss_instruct.py:detect_repo_package','pipelines/code_instruct.py:CodeInstructPipeline.run']}
out=Path('experiments/21-repo2rlenv/evidence/code-instruct-profile');out.mkdir(exist_ok=False)
(out/'biopython.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record))
