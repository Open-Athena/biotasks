# Notebook factory building blocks

BioTasks provides conservative Python notebook conversion, bounded structural
inspection, and an auditable GLM worker transport. These are Python APIs and
prompt assets. A caller supplies task schemas, tool handlers, execution policy,
model access and storage; the package does not provision environments or run an
end-to-end task factory.

## Convert without executing

```python
from pathlib import Path
from biotasks.notebook_script import export_python

script, receipt = export_python(Path("analysis.ipynb"))
Path("analysis.py").write_text(script, encoding="utf-8")
```

The `python-narrative-v5` profile accepts nbformat 4 with an unambiguous Python
language declaration. Jupytext exports ordinary code and retains Markdown cells
as line comments in source order, without cell markers. Raw cells, saved outputs
and presentation metadata are excluded from the script. Conversion never runs
source code, installs dependencies or treats cached output as fresh evidence.

The exporter compares ordered executable Python syntax trees before accepting
its result. Interactive history, top-level await, unsupported execution directives and
unknown code-cell metadata are rejected. The converter records a small explicit
normalization profile: `%matplotlib inline` and a leading `%%time` become
comments, while a literal `%cd` becomes a directory change at the same position.
Other magics remain unsupported. Presentation/editor metadata is recorded; it
does not authorize skipping or changing code. Documentation
execution policy and Jupytext file-pairing metadata are recorded without adopting
them as instructions to skip or alter analysis. Unsupported or malformed inputs
raise `UnsupportedNotebook`; admission failure does not establish poor scientific
quality or an unresolvable dependency problem. Other notebook languages need a
separate export profile.

The receipt records original/script/AST hashes, converter version, code/Markdown
cell counts and execution status. The notebook intake bound is 16 MiB. Preserve
the original notebook and receipt; the script is a reproducible conversion, not a
claim that the analysis executes or is scientifically correct.

## Inspect staged files

```python
from pathlib import Path
from biotasks.data_profile import profile_inputs

report = profile_inputs(
    Path("staged-inputs"),
    [{"path": "observations.tsv", "checksums": {"sha256": "0" * 64}}],
)
```

Replace the example checksum with the recorded source checksum. Files are hashed
by streaming and rejected on mismatch, path escape, symbolic links or changes
during inspection. A source identity is only marked verified when an expected
checksum was supplied and matched. SHA-256 and MD5 source receipts are supported;
SHA-256 is always measured.

CSV/TSV inspection reads a bounded prefix and at most 100 records after the first
record; it does not infer that the first record is a header or that sampled rows
are a whole-dataset count. HDF5 inspection uses `h5py` only when already installed
in the inspection environment and records bounded structure/tiny integer
metadata without assigning biological meanings to axes. Missing readers and
unsupported formats remain explicit unknowns. This does not execute the notebook,
choose task outputs, fit models or materialize complete matrices.

The tool also runs as:

```bash
python -m biotasks.data_profile --root DIR --manifest FILE --output FILE
```

The JSON manifest contains the same explicit file/checksum list;
the output must be a new file. No scientific data or optional HDF5 reader is
installed automatically.

## Record model work and enforce caller allowances

`RequestLedger` in `biotasks.inference_gate` persists request digests and states in
SQLite. Each attempted dispatch reserves a slot before it is sent; an uncertain
transport outcome stays recorded rather than being silently replayed. Request
and output-token allowances are explicit per scope and may be `None`. The ledger
never stores credentials or message contents. It is a local accounting mechanism,
not a provider invoice or a global campaign scheduler.

`InferenceGate` is an optional loopback HTTP adapter for an already-authorized
Chat Completions service. It authenticates scoped requests, applies configured
allowances and forwards model settings. It does not deploy an inference service,
provide a task sandbox or authorize spending. Upstream DNS resolution happens synchronously during construction, before the
listener starts, and its addresses are pinned for the gate lifetime. The system
resolver itself has no cancellable deadline. Once started, request deadlines
include input reads, TCP/TLS establishment and response forwarding; shutdown
interrupts owned sockets and joins request handlers. The caller must close the
gate and manage remote resources independently.

`GLMChatAuthor` in `biotasks.chat_author` receives an asynchronous completion
callback, record writer, ledger, finite deadline and explicit tool handlers. It
supports the `glm-5.3` / `biotasks-glm-chat-v1` runtime used with a free endpoint;
its zero monetary settlements must not be used as paid-provider cost accounting.
No OpenAI SDK, provider credential or endpoint is bundled with the package.

With caller-provided completion/recording functions and a prepared ledger:

```python
from biotasks.chat_author import ChatLimits, GLMChatAuthor

author = GLMChatAuthor(
    complete=completion_callback,
    save_record=record_writer,
    ledger=request_ledger,
    scope="authoring",
    deadline=absolute_deadline,
    limits=ChatLimits(),
)
```

The completion callback receives a request dictionary and returns the complete
response dictionary without hidden retries. The external artifact controller
calls the adapter with its tool schemas/handlers, trace path, model/runtime and
budget. These components are explicit integration points, not package-provided
model access or a ready-to-run authoring command.

The adapter preserves requests, responses, full tool results and provider usage
in caller-selected trace storage. Provider HTTP failures retain safe categories;
raw private error bodies are not copied into public failure receipts. Incomplete
responses cannot execute tools. Recovery is opt-in: caller-provided notices can
allow one empty-response retry, one classified generation retry and one missing
required-tool retry per author instance. An explicit context recovery can keep
the original instructions and latest complete candidate/patch chain after a
recognized context rejection or output-limit stop following tool work. It must
reduce the conversation and retains complete original traces. Context recovery
does not replay a transport-uncertain call. The separate opt-in generation retry
may repeat pure generation after a timeout or normalized model-connection
failure: the backend outcome remains unknown, the original attempted slot and
bookkeeping hold remain retained, and no completed tool action is replayed.
These options use the same request ledger, caller deadline
and turn allowance; none are enabled by default. The transport does not decide
whether a preparation, grading or solver stage should permit them. The caller
owns artifact validation: a successful model response is not a passing scientific
test or a reason to weaken a comparator.

`ChatLimits()` requests native high reasoning and leaves extra input-byte, response-byte,
completion-token and tool-preview caps unset. The request timeout defaults to
600 seconds and every author has a finite caller-supplied deadline. Explicit caps
remain supported and must agree with the ledger; provider context limits still
apply. An optional tool preview keeps the full original output in trace storage.
Callers should select storage carefully: traces can contain source data and model
reasoning and are not automatically safe for public upload.

## Packaged worker prompts

The prompt library includes terminal-export preparation, reference setup,
scientific specification, construction/finalization, independent implementation,
grader authoring, probe generation, review, comparison diagnosis and explicit
recovery notices. Source-backed question defects and independent-implementation
defects are distinct; the external controller must bind evidence, restrict repair
targets and run fresh executable controls. Prompts do not enforce those gates. Inspect
actual assets with `biotasks prompts list` and `biotasks prompts show NAME`.
Templates describe worker contracts but do not implement their schemas or
execution boundaries. The CLI only reads templates; it does not launch workers.

The intended separation is: preserve source, inspect/execute the reference with
separate evidence, let workers author task artifacts, grade outputs
programmatically, and keep answer assets outside solver inputs. Reward comes
from executable grading, while LLM review guides corrections. Reference agreement,
independent recomputation, native execution, blind solving and publication are
distinct evidence stages. These helpers do not establish those outcomes for a
new notebook or demonstrate unattended end-to-end generation.
