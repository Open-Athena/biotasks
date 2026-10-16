"""Package validated worker artifacts using upstream Harbor bundle emission."""

import json
import shlex
from pathlib import Path

from materialization_protocol import Materialization
from reference_environment import UV_VERSION, validate_environment
from repo2rlenv.emitter.bundle import TaskBundle, TaskFile, write_bundle

VERIFY = """import json, subprocess
from pathlib import Path
root = Path('/workspace/outputs')
report = Path('/logs/verifier/report.json')
reward = Path('/logs/verifier/reward.txt')
report.parent.mkdir(parents=True, exist_ok=True)
checks = json.loads(Path('/tests/checks.json').read_text())
required = json.loads(Path('/tests/outputs.json').read_text())
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
                    '--submission-dir',str(root),'--report',str(report)], check=True)
    value = json.loads(report.read_text())
    assert type(value['passed']) is bool
    assert {x['id'] for x in value['checks']} == {x['id'] for x in checks}
    assert len(value['checks']) == len(checks)
    assert all(type(x['passed']) is bool for x in value['checks'])
    assert value['passed'] == all(x['passed'] for x in value['checks'])
reward.write_text('1\\n' if value['passed'] else '0\\n')
"""


def package(*, materialization, grading, environment, destination, name, revision):
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

    load_materialized(materialization)
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
    if not {"reference", "recomputed", "alternative", "empty", "missing", "probe"} <= kinds:
        raise ValueError("Missing native-content or independent comparison controls")
    packages = json.loads((environment / "candidate/system-packages.json").read_text())
    project = (environment / "candidate/pyproject.toml").read_text()
    validate_environment(project, packages)
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
        f"RUN python -m pip install --disable-pip-version-check uv=={UV_VERSION}",
        "RUN UV_PROJECT_ENVIRONMENT=/opt/venv UV_PYTHON_DOWNLOADS=never uv sync "
        "--project /opt/task-environment --locked --no-dev --no-install-project "
        "--python /usr/local/bin/python",
        'ENV PATH="/opt/venv/bin:$PATH"',
        "ENV OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 MKL_NUM_THREADS=4 NUMEXPR_NUM_THREADS=4",
        "COPY inputs/ /workspace/inputs/",
        "RUN chmod -R a-w /workspace/inputs && mkdir -p /workspace/outputs",
        "WORKDIR /workspace",
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
    manifest = json.loads((materialization / "manifest.json").read_text())
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
    return write_bundle(
        TaskBundle(
            name=name,
            org="biotasks",
            instruction=(grading / "instruction.md").read_text(),
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
