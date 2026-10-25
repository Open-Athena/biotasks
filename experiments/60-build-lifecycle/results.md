# Compiled revision lifecycle: mechanism evidence

Eight actual pytest processes with our own tiny CPython extension reproduce the cleanup and stale-binary problems. This is a synthetic mechanism experiment, not a biological task, installed runtime candidate, Docker build or accepted export. Original native stage-builder, output slicing and pytest parser are loaded from hash-bound upstream 27d04ee; only its `/workspace` paths are relocated into owned scratch, and global Git configuration is redirected there. Exact input checkpoint: 7b342465.

| Route | Pre | Post | F2P | P2P |
| --- | --- | --- | --- | --- |
| original_cleanup | collection ERROR | collection ERROR | 0 | 0 |
| preserve_base_binary | FAILED | FAILED | 0 | 1 |
| preserve_head_binary | PASSED | PASSED | 0 | 2 |
| recorded_rebuild | FAILED | PASSED | 1 | 1 |

The tracked header selects return value 0 at base and 1 after the source patch. Each stage has the same two test identities. The unchanged original cleanup removes the compiled module; no test body runs. Preserving base binaries misses the fix. Preserving a bootstrap-head binary passes even against base source and hides the regression. The explicit fixture candidate replays our own originally recorded build command after reset/apply and before tests; source diff and HEAD are checked unchanged by that build. The original parser records one F2P and one P2P. All scripts, full outputs, source hashes, binary hashes and timings are in `compiled-proof.json`.

One local command, one worker/thread, nonblocking heavy lock, 160 MiB estimate; measured peak RSS 39,372 KiB and 3.65 seconds. Load/memory were checked at admission and during the first seconds. Scratch including binaries and local Git configuration was removed in `finally`; no owned `/tmp` path. Zero native jobs/model calls or new spend. Retain proof and sources while cited.

## Source audit and remaining work

Hash-bound `pr_runtime_validate.py:46` builds native stages as reset, clean, patch, tests: no rebuild. `pr_runtime.py:348` builds the task image by resetting and cleaning to PR base, also without rebuilding after that reset. `registry/integration.py:643` creates the inline recipe by checking out the bootstrap ref and replaying its recorded build commands; `_go_inline` appends the task overlay afterward. Therefore replaying bootstrap at HEAD before that overlay does not establish compiled-code correctness at base. The unchanged generated verifier (`pr_runtime.py:435`) restores hidden tests and runs tests after the solver patch, without a project rebuild. This is source-level evidence; no exported image/verifier was run here. Do not assume a generation-only fix covers those later stages.

The actual #58 bootstrap recorded `cd /workspace && pip install -e .`, but replaying arbitrary recorded shell commands at every stage is not yet a qualified generic policy. They can fetch or reset source, install incompatible project versions, modify tests, ignore build failures or reuse stale incremental artifacts; even `pip install -e .` need not force recompilation. Guarding only a tracked diff is insufficient to establish code/import provenance. A general policy needs explicit accepted command forms and actual build/import identity evidence, rejection tests, build failure/timeout handling within the existing deadline, and parity for native stages, base image and post-solver verification. No new package/version, parser/reward, per-task repair or added model stage is authorized by this fixture. No native retry/admission yet.
