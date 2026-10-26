import json,re
from pathlib import Path
p=Path(__file__).resolve().parent
issues={x['number']:x for x in json.loads((p/'overall-review-issues.json').read_text()) if 'pull_request' not in x}
findings={
29:'Eight existing Matchms/OHIF pairs recovered; Scanpy remained timed out at 1,200 seconds. OpenMS acquisition recovered, not task generation. MMseqs bootstrap comparison and general timeout policy remain unmeasured.',
30:'The bounded stdin comparison removed E2BIG and preserved the successful control. PR958 still failed for independent test/environment reasons; no task recovered or production transport change promoted.',
31:'Historical rebuild recovered native MACS PR742 F2P, but exported controls could not fetch isolated build dependencies. The subsequent offline preparation comparison in #34 recovered the clean pair; general compiled policy remains #60.',
32:'Deleted-path targeting and completion-gate diagnostics are recorded, but no biological task was recovered by those candidates. Live acceptance and a stable SAMtools composite-runner contract remain unresolved.',
34:'Offline base-declared wheels recovered the MACS diagnostic with nop 0/oracle 1 and clean oracle exit. Verified receipts and cleanup complete; this is one diagnostic, not fresh generation or general portability.',
35:'Unchanged Cobrapy1482 reproduced clean controls on a different worker. One runtime case establishes selected portability, not portability of the whole cohort.',
36:'Generic cache matching prepared all twelve OHIF exports with unchanged grading assets. Runtime failure and later generic implementation are separately covered by #37 and #65.',
37:'The cold OHIF inline recipe failed before controls because pnpm was absent. This is a completed negative comparison; #39 separately demonstrated recorded-bootstrap replay.',
38:'The manifest controller completed Cobrapy controls and preserved Scanpy build failure. Twelve Cobrapy pairs were positive but only two clean. Recovery, archival and cleanup were verified.',
39:'Recorded bootstrap replay recovered one OHIF clean pair with original grading. Its explicit initializer and hard smoke gates limit transfer; #40 records the negative transfer assessment.',
40:'Source-bound Scanpy assessment found the OHIF wrapper could not transfer unchanged. No new native result was claimed; the bounded assessment is complete.',
41:'Native timeout diagnostics observed surviving writers and transient log holes. The predeclared final-hole conjunction stayed false. Evidence and cleanup complete; no biological causal claim.',
42:'Published Harbor source removes automatic verifier retry but does not establish daemon-side cancellation. The completed source assessment led to #43.',
43:'Baseline timeout writers survived until teardown. Harbor0.24 comparison was inconclusive because its finite trial required unavailable Buildx. No upgrade was adopted.',
44:'Manifest validation extraction and native positive/negative references are complete. Implementation is consolidated in PR #63; merge review belongs there.',
45:'Official known-Cobrapy generation produced an export; reconstruction failed before controls. This completed negative handoff comparison led to #47 and the general interface.',
47:'Generic APT-index refresh recovered builds, then native controls timed out with contradictory late outputs. No positive task accepted; #49 preserved and cleaned the held failure.',
48:'General manifest interface is implemented and consolidated in PR #63. The formerly pending fresh native evidence now exists in #66; this implementation issue needs no separate user review.',
49:'Held-output retention completed with original contradictory bytes and scientific rejection unchanged. Archive readback and cleanup verified; packaging followed in #51.',
51:'Held-failure archival/cleanup support is implemented and consolidated in PR #63. Unknown evidence remains held; no late reward is accepted.',
53:'AnnData completed the unattended lifecycle with zero exports. Imported installed code differed from the patched workspace; provenance follow-up remains #56.',
54:'Ready local stages no longer incur unnecessary five-minute waits. Qualified implementation is consolidated in PR #63; native deadlines remain unchanged.',
56:'Offline pip and same-process pytest fixtures support a code-origin failure mechanism. Native source/import identity qualification and integration remain unresolved; no AnnData repair or acceptance claimed.',
57:'Unchanged Biopython run completed with zero exports because PRs lacked a test patch or a newly named test function. Billing, retention and cleanup are complete.',
58:'The declared official filter option/path policy admitted the PR, but removal of compiled extensions caused collection failure. Zero exports; #60 owns the unresolved rebuild mechanism.',
59:'The optional workspace-rooted pytest-target policy is implemented with real pytest comparisons and consolidated in PR #63. Filename-space parser limitations remain explicit under #32; no broad parser support claimed.',
60:'Offline compiled fixtures show both missing binaries and stale binaries can invalidate historical tests. A revision-aware build/import policy with native/export/post-solver parity remains unqualified.',
61:'Metadata preflight selected an already-known Cobrapy task; execution was deliberately not admitted. Zero calls, jobs or charges; the bounded selection decision is complete.',
62:'Original DendroPy generation produced one export but hit a cache-case handoff hold. #65 subsequently validated that same sealed export without regeneration: tracked-positive, not strict-clean.',
64:'Real subtest fixtures reproduce false PASSED parent identities. Strict clean-command checks reject nonzero exits, but a generic subcase identity or explicit unsupported contract remains unimplemented.',
65:'Sealed DendroPy import and native controls completed without model calls: positive tracked pair, four other failures, zero strict-clean tasks. Archival, cleanup and replay verified.',
66:'Fresh NiBabel generation and independent controls completed: nine target regressions repaired, 37 P2P retained, clean selected-file command. Full lifecycle verified; no whole-repository or dataset-release claim.'}
keep={29,32,56,60,64}
rows=['# Autonomous issue review — 2026-10-26','','Reviewed the live issue bodies, their linked findings, the reconciled task ledger and final delivery audit. This is a review of recorded evidence, not a new execution or regrading. The user requested overall review only; the earlier requirement to leave every child open for human review is superseded. Immutable original bodies are retained in `github/overall-review-issues.json`.','','| Issue | Disposition | Conclusion / remaining work |','| --- | --- | --- |']
plan=[]
for n,reason in findings.items():
 state='OPEN' if n in keep else 'CLOSED'
 rows.append(f'| [#{n}](https://github.com/Open-Athena/biotasks/issues/{n}) | {state} | {reason} |')
 links=re.findall(r'\[[^\]]+\]\(https://github.com/Open-Athena/biotasks/(?:blob|tree)/[^)]+\)',issues[n]['body'])
 evidence=' · '.join(dict.fromkeys(links))
 body=('**Research backlog — agent-owned; no separate user review required.**' if n in keep else '**Closed after agent review of the bounded experiment/delivery.**')+'\n\n'+reason+'\n\n'
 body+=('No new execution is admitted by this status update. ' if n in keep else 'Closure records the bounded result, including its limitations; it does not mean the limitation is fixed or a pipeline change is merged. ')
 body+='Overall findings, costs and remaining work are summarized in epic #33; PR #63 is the consolidated implementation review. Original execution records remain in prior comments and linked research artifacts.\n'
 if evidence: body+='\n'+evidence+'\n'
 (p/f'overall-review-{n}-body.md').write_text(body)
 comment='🤖 Reviewed the recorded findings and lifecycle as part of the overall review requested on 2026-10-26. '+reason+'\n\n'+('Keeping this as substantive agent-owned research backlog, not a request for individual user review.' if n in keep else 'Closing the completed bounded question. No new task, rerun, merge or release is implied.')+' Overall synthesis and per-repository yield/cost are in epic #33.\n'
 (p/f'overall-review-{n}-comment.md').write_text(comment)
 plan.append({'number':n,'state':state,'conclusion':reason})
(p/'overall-review-plan.json').write_text(json.dumps(plan,indent=2)+'\n')
(p.parent/'issue-review-2026-10-26.md').write_text('\n'.join(rows)+'\n')
print(f'{len(plan)} reviewed; {len(plan)-len(keep)} close; {len(keep)} substantive backlog')
