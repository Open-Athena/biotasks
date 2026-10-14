# Plain-script reference execution

This checkpoint implements the first part of the artifact-reproduction proposal:
convert a source, prepare and review a faithful runnable reference, then execute
all its scientific branches offline. It stops before task construction, grading,
blind solving or release. A successful run is reference-execution evidence, not
a validated benchmark task.

## Conversion

`biotasks.notebook_script.export_python(path)` uses pinned Jupytext `py:nomarker`
and verifies the exported Python syntax tree against all source code in order.
It never executes the notebook. The initial admission profile supports ordinary
Python nbformat-4 sources. Kernel-dependent syntax/state and unsupported
execution directives are rejected; R and other formats need separate profiles.
The source document remains the provenance and narrative input. Its stored
outputs do not count as fresh evidence. Documentation build-time execution
policy is recorded without adopting it as a rule to skip analysis.

The first input is the user-selected newer Scanpy clustering notebook. Its
untouched conversion and receipt are in `reference-inputs/scanpy/`, with the
upstream license. The original source URL, revision, hash and data terms are in
`source-manifest.json`; the original source text is in `seeds/current.json`.
There are no Scanpy-specific rules in the converter, prompts or controller.

## Fixed stages and boundaries

1. Create one CPU-only Daytona sandbox and verify its resource configuration.
   Stage the source inventory's original inputs, checking recorded byte sizes
   and upstream checksums and computing SHA-256 hashes.
2. GLM prepares environment setup, minimal source edits for offline input loading
   and exports, and the complete branch-to-artifact inventory.
3. A separate GLM review compares that plan and exact diff with the original
   narrative and unchanged script. Known scientific changes or omitted branches
   block execution. Structural checks do not replace this review.
4. Run setup online under its cumulative allowance. Run the reviewed script in
   a fresh process and empty computation/output directories with network blocked.
   Check provider policy and representative outbound probes. Preserve exit
   status, logs, elapsed time, child RSS, dependency versions and artifact hashes.
   Check that original input files remain unchanged.
5. If setup/exports fail, return the evidence to GLM for a bounded repair and
   review. Analysis defects, resource mismatch or uncertainty may reject the
   source; the factory must not repair science or silently drop branches.

The protocol uses Repo2RLEnv's pinned Tasksmith artifact controller and existing
GLM adapter/request ledger. Calls can submit and revise structured artifacts;
this first reference-preparation configuration does not expose arbitrary shell
tools to the model. Generated setup code executes only in the credential-free
task sandbox. No generated code executes on the credentialed Iris host.

`reference-execution.json` freezes 4 CPUs, 8 GiB RAM, 10 GiB disk, 600 seconds
for complete computation and 1,800 cumulative seconds for data/environment setup.
There are at most three preparation passes (initial plus two repairs), each with
12 preparation requests and three review requests: **45 raw requests total**,
including malformed-response recovery. The whole job has two hours plus five
minutes for cleanup. These are ceilings, not expected usage. The solver time
allowance remains a separate unresolved decision and is not exercised here.

The current model settings allow 32,000 output tokens with medium reasoning.
A completely received, accounted response ending at its output-token limit may
use upstream's one concise recovery within the original stage request allowance.
Partial tools are never executed; uncertain transport outcomes are not retried.

The third campaign reserves $5 from the standing $100 Daytona authorization.
The aggregate reservation becomes $91, leaving $9 unallocated. These conservative
reservations are not measured charges and do not account for any free credits.
One Iris controller uses already approved reserved CPU capacity; GLM uses the
approved free endpoint. No GPU is provisioned.

`launch_reference.payload` freezes inputs from a committed Git revision and
reuses the existing Iris submission/bootstrap mechanism. Submission receipts
are exclusive: an uncertain response requires reconciliation, not redispatch.
Evidence is downloaded, hashed and copied to private durable storage before
sandbox teardown; the existing ownership-label cleanup verifies absence.
The bootstrap exports the final cleanup record as well.

The first run's [record](reference-runs/001/summary.json) preserves a preparation
response-length failure. Data staging and checksums succeeded; no generated setup
or scientific computation ran, and sandbox deletion was verified. The replacement
also fixes the storage-client environment and includes the diagnostic helper in
the frozen payload.

The [second run](reference-runs/002/summary.json) made twelve requests, including
a GLM repair of an offline registry dependency caught by the separate reviewer.
Its next review could not validate: positive findings were placed in a field
reserved for defects. Setup and computation remained blocked; cleanup and
durable export succeeded. The current schema explicitly calls that field
`prohibited_scientific_changes` and requires empty defect lists to approve.
Prompts ask for scientific endpoint data and omit added image capture. The
adapter preserves both current `reasoning` and older `reasoning_content` fields
through tool continuations. The input-byte bound is 512,000 to accommodate those
retained messages; it is not a model context-size claim. Original outputs and
failed reviews remain unchanged in the run records.

## Remaining validation

Passing this reference gate does not establish endpoint semantic fidelity,
portable grading, reproducibility, scientific validity or solver performance.
The next stages must review observed artifacts, validate complete coverage,
freeze the task contract, construct Harbor assets, and run the agreed controls.
Original references, worker proposals and failed attempts remain preserved.
Do not modify generated task-specific science manually.
