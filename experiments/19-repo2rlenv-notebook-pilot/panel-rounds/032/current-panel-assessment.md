# Current ten-source development assessment

Checked 27 October 2026. Issue #19 is incomplete. The table reports the latest completed attempt per source across development versions, including infrastructure failures. It is not a common-version holdout or success-rate estimate.

| Domain | Source | Campaign | Pipeline minutes | Recorded requests | Outcome |
| --- | --- | --- | ---: | ---: | --- |
| Constraint-based metabolism | [cobrapy-deletions](https://github.com/opencobra/cobrapy/blob/a9c5ced29670bed5035fb19e87e7b0b588adb62d/documentation_builder/deletions.ipynb) | [196](../101/result-196.json) | 62.90 | 164 | Generated task omitted a source branch |
| Protein sequence profiles | [pyhmmer-msa-to-hmm](https://github.com/althonos/pyhmmer/blob/90d2f28303d9fe795c4e1ffc1e05b9d634319b51/docs/examples/msa_to_hmm.ipynb) | [199](../101/result-199.json) | 80.49 | 281 | Infrastructure failure after idle sandbox deletion; no accepted final review |
| Metabolite mass spectra | [matchms-spectral-matching](https://github.com/matchms/matchms-docs/blob/796f156c58d25adfb7e1528fcb24eb8c40c143a5/notebooks/matchms_tutorial_01_building_analysis_pipeline.ipynb) | [210](../103/result-210.json) | 114.92 | 187 | Comparison repair passed 13 fresh controls; probe preflight stopped on deadline admission |
| Physiological signals | [neurokit-hrv](https://github.com/neuropsychology/NeuroKit/blob/ff419d983568ef492eb8d229af643c0ef0100b32/docs/examples/ecg_hrv/ecg_hrv.ipynb) | [200](../101/result-200.json) | 37.30 | 167 | Wrong submissions rejected; probe/check attribution and public description disagreed |
| Single-cell transcriptomics | [scanpy-clustering](https://github.com/scverse/scanpy/blob/8c1463d5d97272d5811ad3f4efb57483e23b4c7e/docs/tutorials/basics/clustering.ipynb) | [206](../102/result-206.json) | 20.44 | 45 | Infrastructure failure during session creation; failed operation submitted no command |
| Genomic intervals | [bioframe-motifs-to-peaks](https://github.com/open2c/bioframe/blob/95007ed6fc03b01005d75f95cac511b2df286854/docs/tutorials/tutorial_assign_motifs_to_peaks.ipynb) | [207](../102/result-207.json) | 19.78 | 36 | Autonomous source-fidelity rejection: parser skips a real motif observation |
| Proteomic search results | [pyteomics-filtering](https://github.com/levitsky/pyteomics/blob/a133667b090e41c645ed682861b73d98bef2d045/doc/source/_static/filtering.ipynb) | [208](../103/result-208.json) | 14.32 | 41 | Two setup tests failed; final recipe untested; shell-policy violation retained |
| Molecular dynamics | [mdanalysis-rmsd](https://github.com/MDAnalysis/UserGuide/blob/b20b22d2b050238436c76df0f984be7827854bce/doc/source/examples/analysis/alignment_and_rms/rmsd.ipynb) | [198](../101/result-198.json) | 81.59 | 236 | Qualified/published; native reference/empty/solver rewards 1/0/1 |
| Statistical genetics | [sgkit-relatedness](https://github.com/sgkit-dev/sgkit/blob/a8bc952b6a0b85e156e1bc826597922448ffd078/docs/examples/relatedness_tutorial.ipynb) | [211](../104/result-211.json) | 8.36 | 27 | Original data URLs returned 404; autonomous input-access rejection without substitution |
| Bayesian biological inference | [pymc-rat-tumor](https://github.com/pymc-devs/pymc-examples/blob/17c8f90dc90691b41587dfdf477698d74cf5c18c/examples/generalized_linear_models/GLM-hierarchical-binomial-model.ipynb) | [212](../104/result-212.json) | 22.14 | 54 | Generated setup/export API compatibility conflict; both reference tests failed at the plotting style |

The latest completed outcomes are **one qualified/published task, four rejected generated candidates, one source-fidelity rejection, one original-input-access rejection and three infrastructure failures**. Rejection of a generated candidate does not establish a broken source notebook. Five domains have qualified historical releases. Python only; R remains deferred.

## Active validation

[PyMC 213](../105/development-panel.json) is running on the 105 successor. It receives only the original 186 notebook/provenance: no previous task, answer, export, environment recipe or failure diagnosis. Its 232 runtime files differ from 104 in exactly three files: general native-writer guidance, shorter pre-dispatch control admission, and tests. Source/provider/funding and typed-pool admission passed. All earlier campaign hosts are terminal and their recorded sandbox IDs/owners are verified absent.

The successor has 155 affected tests, 25 preparation/packaging tests and 10 source-admission/AST checks. These are not fresh scientific qualification. A shorter control request is permitted only after a certified pre-dispatch refusal; executed or uncertain outcomes are not retried automatically. Scientific verdicts, required negative controls, original deadlines, resource maxima, two-reference-dispatch limit and repair budgets remain unchanged.

[Matchms 214](../106/development-panel.json) is submitted, initially pending, for a fresh original-source test of the same 232 runtime hashes as 213. Typed admission found only 213 active and verified all earlier terminal cleanup. No previous generated task, answer, environment recipe or diagnostic was supplied.

## Latest qualified release

[MDAnalysis 198](https://huggingface.co/datasets/gonzalobenegas/biotasks-notebook-pilot-issue-19-mdanalysis-rmsd/tree/166d99e941b7e154fc6360f48e739bd19127cfb2) covers five source analyses, passed 19 controls/final reviews, and has native reference/empty/blind-GLM rewards **1/0/1**. Complete original artifacts, cleanup and forced anonymous download are verified. The matching latest viewer shows the notebook, task, attempt and captured pipeline. Its native-ID recording limitations remain explicit. [Release audit](../../autonomous-runs/198/release-audit.json).

This proves one qualified autonomous example; it does not prove reliability across the panel or universal software portability. The same model family/stack contributes to reference and review, limiting independence.

## Recent findings

- **Matchms 210:** the single GLM comparison repair clarified public matrix conventions, after which all 13 fresh basic controls passed, including independent computation. Probe preflight was then refused near the unchanged deadline before dispatch. Mutation controls, final review, native controls and solver remained incomplete. The normal export seal is absent; the original quiescent snapshot independently verifies 3,084 files, plus 67 root files. All five original SDK IDs/owners are absent. No missing seal was reconstructed. The earlier qualified 195 release remains retained. [Result](../103/result-210.json).
- **PyMC 212:** both controlled reference tests failed at the same plotting-style call under the chosen dependency stack. Inspection exposed a conflict between preparation's older wrapper/export APIs and source plotting APIs. Full science/exports never completed. This is a generated-setup compatibility failure; it does not prove that the notebook is broken or no compatible environment exists. All 738 original files, 21 root files and original/fresh cleanup are verified. [Result](../104/result-212.json).
- **Sgkit 211:** both original URLs returned 404 and the storage API reported a missing bucket. No verified original mirror was established, no substitute was accepted, and no reference computation ran. The worker's claim of exhaustive worldwide mirror searching is not accepted. All 284 original files, 19 root files and cleanup are verified. The new input-restaging precheck was not reached. [Result](../104/result-211.json).
- **Sgkit 209:** one controlled reference passed, but strict staged-byte reconstruction failed before replay analysis. The recipe uses volatile gzip metadata; actual replay bytes were not retained, so metadata as the sole cause and identical decoded data are unproved. Input fidelity and redistribution were not accepted. All originals/root exports and cleanup are verified. [Result](../103/result-209.json).
- **Pyteomics 208:** two controlled tests failed on a relative input directory and a plotting-style alias. A final recipe was not tested. Recorded scientific filtering, joins and exports in the setup shell violated the stage prompt and do not count as controlled validation. No operator scientific fix was made. [Result](../103/result-208.json).
- **Bioframe 207:** execution and two replays passed, but source review found that parsing skipped a real motif record. Repeatability did not establish scientific correctness; source fidelity was rejected. [Result](../102/result-207.json).

The [common 232-file baseline](../101/development-panel.json) completed five cases, including qualified MDAnalysis 198. [102](../102/development-panel.json) added the idle-lifecycle correction; [103](../103/development-panel.json) reconciled late-visible session creation on its existing retry; [104](../104/development-panel.json) improved review/coverage feedback and input restaging. Their original outcomes remain preserved and are not relabelled as 105 evidence.

## Remaining work and budget

Validate the general fixes on original-source runs and establish credible reliability across the diverse panel. Initial probe authoring remains blind to hidden grader results. Separating checker attribution from scientific negative coverage is still being considered, not adopted. Owning-worker construction repair still lacks a qualified live example. No scientific gate or reward is relaxed.

A possible future reference-budget change from two dispatches to the same cumulative 20-minute computation maximum remains undecided. Frozen runs retain two dispatches. Pyteomics and Sgkit redistribution remain unestablished.

**$200 authorized / $200 conservative holds / $0 unallocated**, including full $5 reservations for 213 and submitted 214. Complete creation-to-cleanup lifetimes, 300-second margins at both ends, $0.10 margin and upward quarter-dollar rounding retain $1 for Matchms 210, $0.50 for Sgkit 209 and $0.50 for PyMC 212. Their verified refinements release the $5 used for 214. No scientific outcome, invoice, free-credit assumption or new-campaign $5 reservation changes. [Ledger](../../aggregate-budget.json), [210 audit](../103/closed-210-applied.json), [209 audit](../105/closed-209-applied.json), [212 audit](../105/closed-212-applied.json).

Keep #19 open and PR #23 draft/unmerged. Publish only qualified, rights-cleared tasks and verify anonymous downloads. Never merge the research branch; supported promotion requires a fresh branch from main and relevant validation.
