# Notebook-derived task approaches: completed investigation

Issue #17 investigated existing approaches and released examples, built an inspectable notebook/task/attempt Explorer, and ran bounded authoring and solver pilots. The completed scope is assessment of SETA and BixBench as precedents for computational-biology task creation. The original broader goal of developing a reusable authoring prompt was not achieved or silently reclassified as successful. New prompt development is separate future work; no follow-up issue was opened.

Base main commit: `2a1950d239f1ada467c35393991dac87debe35f7`.
Permanent research branch: `codex/research/17-notebook2task`.
Never merge this branch wholesale. Retain it and the cited evidence after closure.

## Conclusions

- BixBench provides notebook/question examples and a documented generation process, but its exact question-authoring prompt was not located in the inspected public sources. It is not a reproducible authoring baseline here.
- The pinned SETA Kaggle recipe has conflicting training instructions, a minimum-model-count gate, EDA-only rejection examples and overly broad modality/keyword exclusions. These constrain its applicability to broader biological analyses. This is not a claim about all SETA adapters. Aggregate and causal effects remain unmeasured.
- A fixed CPU-training variant passed native checks after parent specification edits and a recorded grader repair. This does not establish autonomous authoring, container readiness or transfer.
- The released SETA task's GLM attempt completed with native reward 1.0 (10/10 tests). Review found a feature-selection/CV defect that the original grade did not detect. The original report and grade remain preserved.
- The released BixBench attempt timed out without a submitted answer, then its verifier timed out. It remains unscored; no Together judge call occurred.

## Code and evidence map

All relative links below resolve within a single immutable Git commit when this document is opened through the issue's permalink.

| Work | Code and records |
| --- | --- |
| Explorer, UI and source inventory | [builder](explorer/build.py), [template](explorer/template.html), [approaches](explorer/approaches.html), [catalog](explorer/catalog.json), [published HTML](explorer/index.html), [checks](explorer/check_approaches_browser.py) |
| Trace conversion and viewer | [converter](explorer/trace-viewer/convert_pi.py), [viewer/build instructions and pinned dependencies](explorer/trace-viewer/README.md), [attempt annotations and derived traces](explorer/attempts/) |
| Original baseline prompts | [manifest and snapshots](baselines/seta-v1/manifest.json), [baseline notes](baselines/seta-v1/README.md), [earlier BioTasks draft](../../src/biotasks/prompts/notebook2task.md) |
| Input staging and bounded pilot | [pilot scripts](pilot/), [frozen input manifest](runs/20261006-seta-v1-pilot/input-manifest.json), [initial pilot](runs/20261006-seta-v1-pilot/README.md) |
| GLM authoring runs | [worker/inspection code](glm-pilot/), [all run records](runs/), [variant](variants/cpu-training-v1/README.md) |
| Native validation and repair | [validation code, candidate and two runs](validation/cpu-training-v1/README.md) |
| Third-party solver execution | [bootstrap](attempts/20261007-pi-third-party/bootstrap.py), [proxy](attempts/20261007-pi-third-party/model_proxy.py), [collection](attempts/20261007-pi-third-party/collect.py), [protocol](attempts/20261007-pi-third-party/protocol.json), [task manifest](attempts/20261007-pi-third-party/task-manifest.json), [task packages](attempts/20261007-pi-third-party/tasks/) |
| Original solver evidence | [retention manifest](attempts/20261007-pi-third-party/results/retention-manifest.json), [results](attempts/20261007-pi-third-party/results/), [anonymous retrieval verification](reviews/20261008-retention-verification.json) |
| Independent review | [findings and dispositions](reviews/20261008-independent.md) |
| Historical launch/collection/edit scripts | [sanitized session archive](archive/session-scripts/README.md), [file/hash/redaction manifest](archive/session-scripts/manifest.json) |
| Exact source inputs in HF bucket | [snapshot manifest](archive/input-snapshot-manifest.json), [location and anonymous verification](archive/input-snapshot-receipt.json), [upload/verification code](archive/preserve_inputs.py) |
| Decisions and historical plans | [logbook](logbook.md), [original protocol](protocol.md), [output contract](output-contract.md), [replay API proposal](replay-api.md) |

## Preservation and limits

The small code, prompts, outputs, original solver streams, generated HTML and native checks are retained in Git. Larger exact comparison seeds are retained in the public HF bucket under an append-only manifest-hash prefix; the receipt records anonymous readback verification. Source attribution and benchmark provenance remain attached. These comparison inputs are not training data.

The historical scratch-code archive includes failed attempts and superseded edit scripts as inert text. Private service identifiers are redacted, with replacements recorded. It is not a supported rerun interface. Credentials, private runtime configuration and model transport records are deliberately excluded. The retained evidence does not claim to mirror the entire private orchestrator archive. Credentials and service discovery require the separately maintained private access guidance, not this chat.

No active solver or model deployment needs this session to remain open; the two solver sandboxes were removed. Archiving the chat does not authorize another run, merge, branch deletion or artifact removal. No scientific result depends solely on a screenshot or temporary HTMLPreview cache. The runnable source and generated static pages are both retained; external documentation embeds can still depend on upstream availability.

Historical plans describe work that was considered, not an obligation or authorization to execute it. No general batch runner, accepted transferable prompt, or independent solver assessment of the generated variant was established.
