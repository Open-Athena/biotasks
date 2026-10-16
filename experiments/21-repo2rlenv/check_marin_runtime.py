"""Remote PR-diff native verifier/Marin runtime parity and isolation controls.

Run with the pinned Marin environment after schema validation. No solver or
biological correctness claim: the reward remains native patch similarity.
"""

import asyncio
import base64
import json
import os
import subprocess
from dataclasses import asdict
from pathlib import Path

from shellbox.backends.docker.machine import DockerMachineFactory
from shellbox.machine import Command, MachineSpec, NetworkPolicy, RegistryImage
from taskcompendium.models import ConversationTrace, GradingAttempt, TaskSpec, TextMessage
from taskcompendium.runtime.grading import grade_in_sandbox

ROOT = Path("/evidence/native/runtime")
REGISTRY = "biotasks21-local-registry"
TAG = "localhost:5000/biotasks21/pr2630:base"


def run(argv, *, timeout=900):
    result = subprocess.run(argv, capture_output=True, timeout=timeout)
    with (ROOT / "docker.log").open("ab") as log:
        log.write(result.stdout + result.stderr)
    result.check_returncode()
    return result.stdout.decode().strip()


async def checked(machine, argv):
    result = await machine.run(Command(tuple(argv), timeout=120))
    if result.exit_code != 0:
        raise RuntimeError(f"Command failed: {argv[0]} ({result.exit_code})")
    return result


def materialize(resources, directory):
    directory.mkdir(parents=True, exist_ok=True)
    for resource in resources:
        relative = Path(resource["path"])
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError("Resource escapes destination")
        target = directory / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(base64.b64decode(resource["source"]["content_base64"], validate=True))
        target.chmod(int(resource["mode"], 8))


async def controls(task, image, oracle, verifier):
    factory = DockerMachineFactory()
    spec = MachineSpec(RegistryImage(image), cpus=1, memory_mb=1024, network=NetworkPolicy.DENY)
    records = []
    for case in ("empty", "reference", "unrelated_change"):
        row = {"case": case}
        records.append(row)
        for route in ("native", "marin"):
            learner = await factory.create(spec)
            try:
                await checked(
                    learner,
                    [
                        "sh",
                        "-c",
                        "test ! -e /tests && test ! -e /solution && test ! -e /oracle.patch",
                    ],
                )
                row[route + "_learner_private_paths_absent"] = True
                if case == "reference":
                    await learner.upload(oracle / "patch.diff", "/tmp/candidate.patch")
                    await checked(learner, ["git", "apply", "/tmp/candidate.patch"])
                    await checked(learner, ["rm", "/tmp/candidate.patch"])
                elif case == "unrelated_change":
                    await checked(
                        learner,
                        ["sh", "-c", "printf 'unrelated control\\n' > unrelated-control.txt"],
                    )
                if route == "native":
                    # Native verifier is installed only after learner isolation is checked.
                    await learner.upload(verifier, "/tests")
                    await checked(learner, ["mkdir", "-p", "/logs/verifier"])
                    result = await learner.run(Command(("bash", "/tests/test.sh"), timeout=120))
                    (ROOT / f"{case}-native.log").write_bytes(result.stdout + result.stderr)
                    row["native_exit_code"] = result.exit_code
                    reward = await checked(learner, ["cat", "/logs/verifier/reward.txt"])
                    row["native_reward"] = float(reward.stdout)
                else:
                    attempt = GradingAttempt(
                        ConversationTrace(events=(TextMessage(role="assistant", content="Done."),))
                    )
                    result = await grade_in_sandbox(
                        task, attempt, factory, spec, task_machine=learner, timeout=120
                    )
                    row["marin_result"] = asdict(result)
                    row["marin_reward"] = result.reward
                    # Grader resources must remain absent in the learner after grading.
                    await checked(
                        learner,
                        [
                            "sh",
                            "-c",
                            "test ! -e /tests && test ! -e /solution && test ! -e /oracle.patch",
                        ],
                    )
                    row["marin_postgrade_private_paths_absent"] = True
            finally:
                await learner.close()
            (ROOT / "controls.json").write_text(json.dumps(records, indent=2) + "\n")
        assert row["native_exit_code"] == 0
        assert row["marin_result"]["status"] == "graded", row
        assert row["native_reward"] == row["marin_reward"], row
    assert records[0]["native_reward"] == 0
    assert records[1]["native_reward"] == 1
    assert records[2]["native_reward"] < 1
    (ROOT / "result.json").write_text(
        json.dumps(
            {
                "status": "runtime_parity_controls_passed",
                "cases": records,
                "reward_semantics": "native_patch_similarity_not_functional_correctness",
                "image": image,
                "model_calls": 0,
            },
            indent=2,
        )
        + "\n"
    )


def main():
    if os.environ.get("REPO2RLENV_REMOTE_WORKER") != "1":
        raise RuntimeError("Remote worker required")
    ROOT.mkdir()
    data = json.loads(Path("/work/native/task.json").read_text())
    build = ROOT / "build"
    materialize(data["environment_requirements"]["docker_build"]["files"], build)
    oracle, verifier = ROOT / "oracle", ROOT / "verifier"
    materialize(data["resources"]["oracle"], oracle)
    materialize(data["resources"]["verifier"], verifier)
    try:
        run(
            [
                "docker",
                "run",
                "-d",
                "--name",
                REGISTRY,
                "--memory",
                "128m",
                "--cpus",
                "0.25",
                "-p",
                "127.0.0.1:5000:5000",
                "registry:2",
            ]
        )
        run(["docker", "build", "-t", TAG, str(build)], timeout=1800)
        run(["docker", "push", TAG])
        image = json.loads(
            run(["docker", "image", "inspect", TAG, "--format", "{{json .RepoDigests}}"])
        )[0]
        environment = data["environment_requirements"]
        environment.pop("docker_build")
        environment["docker_image"] = image
        data["grader"]["environment"] = dict(environment)
        task = TaskSpec.model_validate(data)
        (ROOT / "resolved-task.json").write_text(task.model_dump_json(indent=2) + "\n")
        asyncio.run(controls(task, image, oracle, verifier))
    finally:
        result = subprocess.run(["docker", "rm", "-f", REGISTRY], capture_output=True)
        (ROOT / "registry-cleanup.json").write_text(
            json.dumps({"returncode": result.returncode}) + "\n"
        )


if __name__ == "__main__":
    main()
