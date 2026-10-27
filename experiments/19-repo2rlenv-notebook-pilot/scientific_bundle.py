"""Package validated worker artifacts using upstream Harbor bundle emission."""

import json
import shlex
from pathlib import Path

from grader_support import MANIFEST, MODULE, load_support
from materialization_protocol import Materialization
from reference_environment import UV_VERSION, validate_environment
from repo2rlenv.emitter.bundle import TaskBundle, TaskFile, write_bundle

VERIFY = """import hashlib, json, os, subprocess
from pathlib import Path
root = Path('/workspace/outputs')
report = Path('/logs/verifier/report.json')
reward = Path('/logs/verifier/reward.txt')
report.parent.mkdir(parents=True, exist_ok=True)
reward.unlink(missing_ok=True)
report.unlink(missing_ok=True)
checks = json.loads(Path('/tests/checks.json').read_text())
required = json.loads(Path('/tests/outputs.json').read_text())
trusted_inputs = Path('/tests/inputs')
expected_inputs = json.loads(Path('/tests/inputs-manifest.json').read_text())
def verify_inputs():
    if trusted_inputs.is_symlink() or not trusted_inputs.is_dir():
        raise ValueError('Unsafe verifier input directory')
    actual = {}
    for path in trusted_inputs.rglob('*'):
        if path.is_symlink() or not (path.is_file() or path.is_dir()):
            raise ValueError('Unsafe verifier input')
        if path.is_file():
            with path.open('rb') as stream:
                actual[path.relative_to(trusted_inputs).as_posix()] = hashlib.file_digest(stream, 'sha256').hexdigest()
    if actual != expected_inputs:
        raise ValueError('Verifier input identities changed')
verify_inputs()
unsafe = root.is_symlink()
for name in required:
    path = root
    for component in Path(name).parts:
        path = path / component
        if path.is_symlink():
            unsafe = True
        if path.exists() and not (path.is_file() or path.is_dir()):
            unsafe = True
if unsafe:
    value = {'passed': False, 'checks': [dict(id=c['id'], passed=False,
             message='Submission contains unsafe paths') for c in checks]}
    report.write_text(json.dumps(value))
else:
    subprocess.run(['python','/tests/grade.py','--reference-dir','/tests/reference',
                    '--submission-dir',str(root),'--report',str(report)], check=True,
                   env={**os.environ, 'BIOTASKS_TRUSTED_INPUT_DIR': str(trusted_inputs)})
    verify_inputs()
    value = json.loads(report.read_text())
    assert type(value['passed']) is bool
    assert {x['id'] for x in value['checks']} == {x['id'] for x in checks}
    assert len(value['checks']) == len(checks)
    assert all(type(x['passed']) is bool for x in value['checks'])
    assert value['passed'] == all(x['passed'] for x in value['checks'])
reward.write_text('1\\n' if value['passed'] else '0\\n')
"""


def runtime_instruction(instruction):
    """Append host-controlled paths without editing the authored scientific contract."""
    return (
        instruction.rstrip()
        + "\n\n## Task directories\n\n"
        + "Read the supplied inputs from `/workspace/inputs/`. "
        + "Write all required output files under `/workspace/outputs/`, "
        + "using the relative filenames specified above. "
        + "The working directory is `/workspace`. "
        + "Aliases `/inputs/` and `/outputs/` refer to these same directories.\n"
    )


def package(
    *, materialization, grading, environment, destination, name, revision, attribution=None
):
    materialization, grading, environment = map(Path, (materialization, grading, environment))
    candidate = Materialization.model_validate_json(
        (materialization / "candidate.json").read_text()
    )
    result = json.loads((grading / "result.json").read_text())
    controls = json.loads((grading / "final-controls.json").read_text())
    grader = json.loads((grading / "final-candidate.json").read_text())
    if (
        candidate.disposition != "ready"
        or result["status"] != "grader_candidate_validated"
        or not result["cleanup_verified"]
        or not controls
        or not all(c["passed_control"] for c in controls)
    ):
        raise ValueError("Validated grading and verified cleanup required before packaging")
    from materialization_inputs import load_materialized
    from reference_replay import sha256

    _, materialized_execution = load_materialized(materialization)
    if any(c["candidate_sha256"] != sha256(grading / "final-candidate.json") for c in controls):
        raise ValueError("Controls belong to a different grader candidate")
    expected_instruction = (
        candidate.instruction.rstrip()
        + "\n\n## Acceptance rules\n\n"
        + grader["instruction"]
        + "\n"
    )
    if (grading / "instruction.md").read_text() != expected_instruction:
        raise ValueError("Public instructions differ from the validated composition")
    kinds = {c["kind"] for c in controls}
    if (
        not {"reference", "recomputed", "alternative", "empty", "misplaced", "missing", "probe"}
        <= kinds
    ):
        raise ValueError("Missing native-content or independent comparison controls")
    packages = sorted(
        set(json.loads((environment / "candidate/system-packages.json").read_text())) | {"tmux"}
    )
    project = (environment / "candidate/pyproject.toml").read_text()
    validate_environment(project, packages)
    from reference_replay import load_dependency_exclusions

    environment_manifest = (
        json.loads((environment / "artifact-manifest.json").read_text())
        if (environment / "artifact-manifest.json").exists()
        else {"files": []}
    )
    exclusions = load_dependency_exclusions(
        environment, {item["path"]: item["sha256"] for item in environment_manifest["files"]}
    )
    from materialization_environment import effective_exclusions

    exclusions = effective_exclusions(exclusions, candidate.model_dump(), materialized_execution)
    # This infrastructure wrapper never authors scientific task code or values.
    docker = ["FROM python:3.13.13-slim-bookworm", "ENV DEBIAN_FRONTEND=noninteractive"]
    if packages:
        docker.append(
            "RUN apt-get update && apt-get install -y --no-install-recommends "
            + shlex.join(packages)
            + " && rm -rf /var/lib/apt/lists/*"
        )
    docker += [
        "COPY pyproject.toml uv.lock /opt/task-environment/",
        f"RUN python -m pip install --no-cache-dir --disable-pip-version-check uv=={UV_VERSION}",
        "RUN UV_NO_CACHE=1 UV_PROJECT_ENVIRONMENT=/opt/venv UV_PYTHON_DOWNLOADS=never uv sync "
        "--project /opt/task-environment --locked --no-dev --no-install-project "
        "--python /usr/local/bin/python",
        'ENV PATH="/opt/venv/bin:$PATH"',
        "ENV OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 MKL_NUM_THREADS=4 NUMEXPR_NUM_THREADS=4",
        "COPY inputs/ /workspace/inputs/",
        "RUN chmod -R a-w /workspace/inputs && mkdir -p /workspace/outputs"
        " && ln -s /workspace/inputs /inputs && ln -s /workspace/outputs /outputs",
        "WORKDIR /workspace",
    ]
    if exclusions is not None:
        # Private reasons can contain reference observations. Do not put them,
        # the deletion recipe, or a backup answer into the solver filesystem.
        docker += [
            "COPY dependency_assets.py dependency-exclusions.json /opt/task-environment/",
            "RUN /opt/venv/bin/python /opt/task-environment/dependency_assets.py "
            "/opt/task-environment/dependency-exclusions.json /opt/task-environment/exclusions-applied.json "
            "&& rm /opt/task-environment/dependency_assets.py /opt/task-environment/dependency-exclusions.json "
            "/opt/task-environment/exclusions-applied.json",
        ]
    assets = {
        "environment/Dockerfile": TaskFile.text("\n".join(docker) + "\n"),
        "environment/pyproject.toml": TaskFile.text(project),
        "environment/uv.lock": TaskFile((environment / "trial/uv.lock").read_bytes()),
        "solution/oracle.py": TaskFile.text(candidate.oracle_code + "\n"),
        "solution/solve.sh": TaskFile.text(
            "#!/bin/sh\nset -eu\ncd /workspace\n"
            "mkdir -p outputs\npython /solution/oracle.py --input-dir inputs --output-dir outputs\n",
            executable=True,
        ),
        "tests/grade.py": TaskFile.text(grader["grader_code"] + "\n"),
        "tests/checks.json": TaskFile.text(json.dumps(grader["checks"]) + "\n"),
        "tests/outputs.json": TaskFile.text(json.dumps(candidate.output_paths) + "\n"),
        "tests/verify.py": TaskFile.text(VERIFY),
        "tests/test.sh": TaskFile.text(
            "#!/bin/sh\nset -eu\npython /tests/verify.py\n", executable=True
        ),
    }
    support = load_support(grading, result.get("parsing_support"))
    if support is not None:
        if any(c["execution"].get("parsing_support") != support for c in controls):
            raise ValueError("Control parsing support differs from its packaged source")
        assets["tests/" + MODULE] = TaskFile((grading / MODULE).read_bytes())
        assets["tests/" + MANIFEST] = TaskFile((grading / MANIFEST).read_bytes())
    if exclusions is not None:
        assets["environment/dependency_assets.py"] = TaskFile(
            (environment / "trial/dependency_assets.py").read_bytes()
        )
        public_manifest = {
            "files": [
                {key: item[key] for key in ("distribution", "path", "sha256")}
                for item in exclusions["files"]
            ]
        }
        assets["environment/dependency-exclusions.json"] = TaskFile.text(
            json.dumps(public_manifest, indent=2) + "\n"
        )
    if attribution is not None:
        # Attribution is frozen before native trials, so the released executable
        # bundle identity includes the notices rather than adding them afterward.
        assets["environment/SOURCE-LICENSES.json"] = TaskFile.text(
            json.dumps(attribution, indent=2) + "\n"
        )
        source_license = attribution.get("notebook_license", {})
        if source_license.get("text"):
            assets["environment/LICENSE.source"] = TaskFile.text(source_license["text"])
    manifest = json.loads((materialization / "manifest.json").read_text())
    assets["tests/inputs-manifest.json"] = TaskFile.text(
        json.dumps({item["path"]: item["sha256"] for item in manifest["inputs"]}) + "\n"
    )
    for kind, names, prefix in [
        ("inputs", candidate.input_paths, "environment/inputs"),
        ("reference", candidate.output_paths, "tests/reference"),
    ]:
        records = {p["path"]: p for p in manifest[kind]}
        for relative in names:
            path = materialization / kind / relative
            if (
                path.is_symlink()
                or path.stat().st_size != records[relative]["bytes"]
                or sha256(path) != records[relative]["sha256"]
            ):
                raise ValueError("Materialized bundle bytes differ from evidence")
            assets[prefix + "/" + relative] = TaskFile(path.read_bytes())
            if kind == "inputs":
                assets["tests/inputs/" + relative] = TaskFile(path.read_bytes())
    return write_bundle(
        TaskBundle(
            name=name,
            org="biotasks",
            instruction=runtime_instruction((grading / "instruction.md").read_text()),
            files=assets,
            metadata={
                "recipe": "notebook-artifact-reproduction",
                "recipe_version": revision,
                "reward_kinds": ["binary"],
                "scope": "scientific task with explicit supplied intermediates",
            },
            environment={
                "cpus": 4,
                "memory_mb": 8192,
                "storage_mb": 10240,
                "build_timeout_sec": 600,
                "network_mode": "no-network",
            },
            agent_timeout_sec=600,
            verifier_timeout_sec=120,
        ),
        Path(destination),
    )
