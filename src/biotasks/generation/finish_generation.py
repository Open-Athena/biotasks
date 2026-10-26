"""Consume only fully completed source-bound generation; never drive imports."""

from pathlib import Path

from biotasks.generation import resources, run_generation
from biotasks.generation.generation_pipeline import GenerationPipeline
from biotasks.validation.files import MAX_ARCHIVE, MAX_FILE, read_json, require, safe, sha
from biotasks.validation.journal import STAGES


def verify_generation_source(directory, readback):
    # Native archives already enforce these byte bounds. History batches may
    # legitimately contain more than the small-input inventory's 1,000 files.
    root = directory / "generation-source"
    require(root.is_dir() and not root.is_symlink(), "Unsafe generation source")
    expected = [{**row, "mode": oct(row["mode"])[2:]} for row in readback["source_members"]]
    require(len(expected) <= 10_000, "Generation evidence exceeds 10000 files")
    rows, total = [], 0
    for path in root.rglob("*"):
        require(not path.is_symlink(), "Symlinked generation evidence")
        if not path.is_file():
            continue
        size = path.stat().st_size
        total += size
        require(size <= MAX_FILE and total <= MAX_ARCHIVE, "Generation evidence exceeds byte bounds")
        rows.append({"path": safe(path.relative_to(root).as_posix()), "bytes": size,
                     "mode": oct(path.stat().st_mode & 0o777)[2:], "sha256": sha(path)})
        require(len(rows) <= 10_000, "Generation evidence exceeds 10000 files")
    rows.sort(key=lambda row: row["path"])
    require(rows == expected, "Extracted raw/cache lineage differs from verified original generation")


def generation_ready(root):
    plan = run_generation.verify(root, allow_legacy=True)
    directory = root / "runs" / plan["group"]["id"]
    held = directory / "held.json"
    if held.exists():
        return {"state": "held", "reason": read_json(held)["reason"]}
    path = directory / "journal.json"
    if not path.exists() or [s["stage"] for s in read_json(path)["stages"]] != list(STAGES):
        return {"state": "waiting_for_existing_generation", "run_id": plan["group"]["run_id"]}
    imported = (
        "generation_code_identity" in plan
        and plan["generation_code_identity"] != resources.code_identity()
    )
    if not imported:
        pipeline = GenerationPipeline(root, plan, plan["group"])
        require(pipeline.step() == "complete", "Generation journal is not independently complete")
    readback = read_json(directory / "readback.json")
    if not readback["model_billing"]["complete"] or any(
        (directory / name).exists()
        for name in (
            "budget-hold.json",
            "model-budget-hold.json",
            "cleanup/budget-hold.json",
            "stop/budget-hold.json",
        )
    ):
        return {"state": "held", "reason": "Generation accounting hold; preserve the original run"}
    if readback["exported_tasks"]:
        verify_generation_source(directory, readback)
    bindings = {
        name: sha(directory / name)
        for name in (
            "journal.json",
            "readback.json",
            "cleanup-proof.json",
            "preserved/manifest.json",
            "publication.json",
            "cleanup/preserved/manifest.json",
            "cleanup/publication.json",
        )
    }
    return {
        "state": "ready",
        "plan": plan,
        "readback": readback,
        "directory": directory,
        "binding": {
            "generation_plan_sha256": sha(root / "plan.json"),
            "generation_evidence": bindings,
            "connector_sha256": sha(Path(__file__)),
            **(
                {
                    "read_only_completed_import": True,
                    "original_generation_code_identity": plan["generation_code_identity"],
                    "consumer_generation_code_identity": resources.code_identity(),
                }
                if imported
                else {}
            ),
        },
    }
