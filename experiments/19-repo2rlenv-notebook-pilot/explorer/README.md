# Notebook → task → attempt explorer

`index.html` is standalone: it embeds the latest selected notebook, published
question, successful native solver trajectory and nine pipeline stages. Each
stage separates recorded prompts, inputs and outputs. Code has syntax
highlighting; detailed records are collapsed. The notebook view shows source
cells, not stale saved outputs. Model reasoning is omitted from the reading
view; original trajectories remain linked.

The current selection is preparation 010, setup 001, replay 001, specification
016, materialization 006, grading 006, native 003 and scientific release 001.
Grading includes the component prompts that produced the accepted grader.
This is a current evidence explorer, not a campaign log.

Build with `python experiments/19-repo2rlenv-notebook-pilot/explorer/build.py`
using markdown-it-py and Pygments from the recorded upstream environment. All
inputs are versioned: no private archive or credential is needed. The `evidence`
folder contains recovered exact worker inputs and the two small published task
files. `source-manifest.json` records embedded file hashes and release identity.
GitHub links pin the checkout revision at build time; commit new evidence before
building for publication. HTML escapes code and disables raw Markdown HTML.

`check_browser.py` checks view/stage navigation, the solver trace and mobile
layout using Playwright and the node's Chromium. Large biological inputs and
reference outputs are linked through release manifests rather than embedded.
