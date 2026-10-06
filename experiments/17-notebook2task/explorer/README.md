# Notebook and task-idea explorer

`catalog.json` is the editable source of descriptions, assistant proposals,
source links, historical #10 records, and limitations. `template.html` supplies
presentation and interactions. `build.py` embeds the catalog into `index.html`.
Rebuild with `uv run --locked python experiments/17-notebook2task/explorer/build.py`.
The builder uses the locked development environment's Markdown renderer for the
full bedtools source snapshot. No network is needed to build.

The current shortlist has 12 candidates across five repositories, including
nine notebooks and three analysis-document entries. Atlas was removed at the
user's request because the identified source was an API guide, not a notebook.
The legacy PBMC3k introduction was removed in favor of the current Scanpy
preprocessing tutorial. Current Scanpy GitHub source links were refreshed to
`7ad567d9f7ca52b23b0ffb964e486034ef14283e` on October 6, 2026. Seven entries
retain unchanged historical inspection records from issue #10 for provenance;
those records do not claim validation of the refreshed source versions.

The current Scanpy tutorial uses real donor measurements from the NeurIPS 2021
single-cell benchmark. Gonzalo clarified that this is not an LLM benchmark and
is not an exclusion for this study. Its provenance remains visible; ordinary
terms and overlap checks relevant to our model evaluations remain pending.

## Full original source view

The default view embeds the authors' rendered tutorial/documentation, not
nbviewer. “Original tutorial / documentation” and “Original source on GitHub”
are always explicit links. nbviewer remains an optional separate link for
notebooks; reported 503s need not prevent viewing the original documentation.
Author-hosted documentation can change independently of the pinned source.

The bedtools website failed a browser load check, so its full original Markdown
is rendered locally from `snapshots/bedtools.md`, alongside the upstream MIT
license. The snapshot was retrieved from the pinned source linked in the catalog.
The builder records its SHA-256 in the embedded catalog. Source code and prose
are preserved; raw HTML is escaped and external images may require internet.

Frames are sandboxed. Remote author documentation can run its rendering
JavaScript for math and widgets; the local bedtools snapshot has scripts disabled.
No notebook kernel, model inference, biological data retrieval, or scientific
execution is involved. Saved outputs remain historical display evidence. The shortlist
and bedtools text work offline; other full-source views require internet. A
separate original-source link remains available for framing or network failures.

`check_browser.py` covers the catalog controls and mobile width.
`check_notebook.py` checks every full-source view and both original links.
Both need an existing Playwright/Chromium installation and the shared-node guard.
No generated or accepted tasks exist. The shortlist is not the run input manifest.
