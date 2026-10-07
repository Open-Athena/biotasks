"""Group vignette representations; prefer authoring source for LLM input.

Only same-version, same-directory Bioconductor vignette stems are paired.
Arbitrary repository files with matching stems are not assumed equivalent.
"""
from pathlib import PurePosixPath
from urllib.parse import urlsplit

AUTHORING = {'R Markdown', 'Quarto', 'Sweave/knitr', 'Jupyter', 'marimo', 'Pluto', 'Jupytext', 'Wolfram notebook', 'MATLAB Live Script', 'Livebook', '.NET Interactive'}

def consolidate(documents):
    groups = {}
    for n in documents:
        path = urlsplit(n['url']).path
        is_vignette = '/vignettes/' in path and '/inst/doc/' in path
        # Mirror hosts share the same versioned Bioconductor path.
        host = urlsplit(n['url']).hostname
        known_host = host in {'bioconductor.org', 'bioconductor.posit.co'}
        key = ('vignette', str(PurePosixPath(path).with_suffix(''))) if is_vignette and known_host else ('artifact', n['url'], n['path'])
        groups.setdefault(key, []).append(dict(n))
    result = []
    for key, items in groups.items():
        def priority(n):
            return 0 if n['format'] in AUTHORING else 2 if n['format']=='Vignette R script' else 1
        ordered = sorted(items, key=priority)
        primary = ordered[0]
        for n in ordered:
            n['role'] = 'Authoring source' if n['format'] in AUTHORING else 'Extracted R code' if n['format']=='Vignette R script' else 'Rendered output' if n['format']=='Rendered vignette' else 'Document'
        source = primary['format'] in AUTHORING
        result.append({**primary, 'representations':ordered, 'authoring_source_located':source, 'grouping':'Same versioned vignette stem' if key[0]=='vignette' else 'Single artifact; equivalence not inferred', 'llm_input': 'Prefer authoring source; use rendered output only when outputs are needed.' if source else 'Authoring source not recovered; retain this representation as a fallback.'})
    return result
