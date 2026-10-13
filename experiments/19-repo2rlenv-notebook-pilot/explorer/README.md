# Notebook pilot evidence explorer

Open `index.html` locally, or use HTMLPreview on its GitHub URL. The standalone
page has no runtime dependencies or remote scripts. It follows issue 17's static
HTML explorer approach and visual conventions, with links to the existing Harbor
Visualiser. It does not execute notebooks, models or task tools.

The view contains the captured notebook source text, task files, exact captured
model inputs/outputs, final controls and selected historical solver trajectories.
Design/build prompts come from campaign 009; final review/repair prompts come from
018. This is selected evidence, not a reconstruction of all historical campaigns.
Current prompt templates are labeled separately from the prompts actually used.
The post-release grading defect remains prominent until a repaired release exists.

`build.py` reads the recovered campaign archives at its explicit local paths.
Those archives are operator inputs, not expected to exist in a fresh checkout.
The generated page is self-contained; no private model route or credential is
required to view it. Archived input/output strings are rendered with textContent,
not interpreted as HTML. Source license notices are included.

Browser checks exercised all five tabs, every prompt/attempt selector and a
390-pixel mobile viewport: no JavaScript errors or horizontal overflow. Exact
credential and private-marker scans passed before publication.
