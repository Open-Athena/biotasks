"""Check the pinned native caller's local Docker requirement without model calls."""
import hashlib
import inspect
import json
import os
import shutil
from pathlib import Path
from repo2rlenv.bootstrap import docker
from repo2rlenv.pipelines import equivalence_tests


def main():
    if not os.environ.get('IRIS_OUTPUT_DIR'):
        raise RuntimeError('Run in the authorized Iris controller runtime')
    files={}
    for module in (docker,equivalence_tests):
        path=Path(inspect.getfile(module))
        files[module.__name__]=hashlib.sha256(path.read_bytes()).hexdigest()
    start=inspect.getsource(equivalence_tests.EquivalenceTestsPipeline._start_sandbox)
    author=inspect.getsource(equivalence_tests.EquivalenceTestsPipeline._llm_generate_test)
    assert 'DockerSandbox.start(' in start and 'resp = complete(' in author
    available=False;error=None
    try:available=docker.is_docker_available()
    except (FileNotFoundError,PermissionError) as exc:error=type(exc).__name__
    result={'stage':'native_equivalence_controller_backend_preflight',
            'status':'backend_available_generation_unexecuted' if available else 'native_controller_docker_unavailable',
            'native_module_sha256':files,'docker_binary_present':shutil.which('docker') is not None,
            'native_docker_availability_check':available,'availability_exception_type':error,
            'native_model_and_docker_calls_run_on_same_caller':True,
            'model_calls':0,'worker_allocations':0,'task_generation_attempts':0,
            'scope':'Same pinned native pipeline/backend requirement for both Python panel repositories; not repository-specific build evidence.',
            'limitations':['Does not test inference or move credentials to a tool sandbox.','Does not test any additional transport/proxy/colocation adaptation.','Learner-visible native reference remains a separate curation limitation even if backend becomes available.']}
    output=Path(os.environ['IRIS_OUTPUT_DIR']);output.mkdir(parents=True,exist_ok=True)
    (output/'native-equivalence-backend.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result))


if __name__=='__main__':main()
