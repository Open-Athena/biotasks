# Notebook pilot evidence explorer

Open `index.html` locally or through HTMLPreview. The standalone page uses the
layout, artifact cards, Markdown rendering and code styling of the issue 17
explorer at commit `9819917efaf925d51e10f06e19ef056cd964c91c`. Its Approaches view
now shows this pilot's actual notebook intake, SETA authoring, quality/repair,
solver and release stages. The notebook workspace separates Notebook, Task,
Attempt and Review, with exact recorded prompts available by pipeline stage.

`release-status.json` identifies the published revision and validation limits.
Design/build calls come from campaign 009; selected quality and repair calls
come from 018, 020 and 022. Historical solver attempts retain their original
bundle identities. The displayed task and final controls come from campaign 022.
Current guidance templates are separate from the recorded historical inputs.

`build.py` reads recovered campaign archives at explicit local paths. These are
operator inputs, not expected to exist in a fresh checkout. Build with the
recorded upstream environment (markdown-it-py 4.0.0 and Pygments):

```bash
python experiments/19-repo2rlenv-notebook-pilot/explorer/build.py \
  --campaign 22 \
  --status experiments/19-repo2rlenv-notebook-pilot/explorer/release-status.json
```

The generated page needs no private route, credentials, runtime dependency or
remote script. Raw notebook HTML is disabled during Markdown rendering; code is
escaped by Pygments. All other archived strings use textContent. The source
notebook is rendered cell by cell; source outputs remain available at the pinned
original link. License notices are included.

Browser checks exercise both top-level views, all five pipeline stages, every
prompt/attempt selector and a 390-pixel viewport. Credential/private-marker scans
run before publication. The review explicitly distinguishes static assessment
of the two repaired coercion defects from the fresh native control trials.

Task design and construction are separate steps. The upstream design call returns
`draft_spec` in structured JSON; the builder receives it as `design.draft_spec`.
The inherited prompt mentions `draft_spec.md`, but this direct-call pathway does
not require that intermediate file. Recorded prompts remain unchanged.

Model calls show separate Input and Output sections. Prompts and generated draft
specifications are rendered as Markdown; additional seed/context and exact API
records are collapsed. Reading views normalize literal escaped newlines when a
model returned a single escaped line. Original records remain unchanged in
Technical details, preserving the exact request hash and response receipt.

During prompt review, Task design and Task construction show the canonical
packaged prompt files used by the launcher, rather than old recorded calls.
Outputs for the revised prompts are explicitly pending a new run. These prompt
edits do not retroactively change the completed task or its validation evidence.
