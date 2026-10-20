# Notebook → task → attempt explorer

`index.html` is standalone. It embeds the selected notebook, task question,
solver trajectory when recorded, and pipeline evidence. Each stage separates
prompts, inputs and outputs. Code has syntax highlighting; detailed records are
collapsed. The notebook view shows source cells rather than treating saved
outputs as fresh results. Model reasoning is omitted from the reading view;
original trajectories remain linked. This is an evidence explorer, not a campaign
log.

`current.json` selects the default evidence. Other profiles select the same layout
without changing the renderer. Control counts and solver rewards come from the
selected records. A profile without validation or an attempt displays that absence;
it does not borrow results from another task. Missing declared evidence is an
error, and a solver selection must identify exactly one trajectory.

Build from the repository root using Python with markdown-it-py and Pygments
available in the recorded upstream environment:

```bash
python experiments/19-repo2rlenv-notebook-pilot/explorer/build.py
```

Review another selection without replacing the published index:

```bash
python experiments/19-repo2rlenv-notebook-pilot/explorer/build.py \
  --profile experiments/19-repo2rlenv-notebook-pilot/transfer/bioframe/explorer-profile.json \
  --output /tmp/biotasks-explorer-review
```

All reading inputs are versioned; building does not require a private archive,
credential, model call or biological data download. Evidence folders preserve
exact recovered worker inputs with their source hashes. `source-manifest.json`
records the profile, embedded file hashes, selected trajectory size and release
identity when available. GitHub links pin the checkout revision at build time;
commit new evidence before building for publication. HTML escapes code and
disables raw Markdown HTML.

`check_browser.py --index /tmp/biotasks-explorer-review/index.html` checks
view/stage navigation, the selected solver trace and mobile layout using
Playwright and the node's Chromium. Large biological inputs and reference outputs
are represented by manifests and linked through the release when published.
