# Recorded-bootstrap comparison completion audit

The bounded OHIF #5996 comparison and its evidence lifecycle are complete. Keep the research issue open for review. This does not establish production readiness or a cohort-wide result.

| Gate | Verified outcome |
| --- | --- |
| Source and comparison | Pinned Repo2RLEnv 27d04ee8, same original public base image as #37, all eighteen original actions and original smoke/fresh checks; no command repairs or model calls |
| Candidate grading contract | Eight original grading/instruction/oracle assets and original overlay unchanged; only explicit dependency reference and native local-only provenance differ |
| Static and lifecycle checks | Native static validation 0 errors / 0 warnings; twelve offline checks; actual watcher interruption/recovery with identical submission/input hashes |
| Fresh bootstrap | Eighteen matching exits; smoke passed; fresh image check exited 0, with 121 suites / 1446 tests passing |
| Independent task controls | Nop reward 0: 0/26 F2P, 1189/1189 P2P; oracle reward 1: 26/26 F2P, 1189/1189 P2P, exit 0, zero untracked failures |
| Source/dependency binding | Both pre-control images at the original base commit; exact ancestry to one reconstructed dependency ID; equal measured tool/package/lock/PATH probes. Image IDs differ, so no image-byte-identity claim |
| Durability | Eight public input objects cold-read before execution; thirteen runtime objects and nested members anonymously verified after worker cleanup; final three-object / 74-member summary/source snapshot verified anonymously |
| Budget and remote cleanup | One terminal attempt, 0.5101238889164394 allocated CPU-hours; unused cleanup allowance released; every owned container/controller/image/volume removed |
| Local cleanup | 2,172,322 redundant logical bytes deleted after verified preservation; immutable payload/canonical stage evidence retained with review conditions; no task-owned /tmp paths |
| Completed reinvocation | Fourteen stage/budget files remain byte-identical before and after local cleanup; no new submission or model calls |

The result supports an environment-export fidelity omission for this frozen task: original recorded bootstrap replay recovers the original controls while the native clean recipe fails at missing pnpm. The initializer remains required. Anonymous input availability and a cold rebuild do not promise future third-party service availability, deterministic dependency resolution across time, or a standalone task Dockerfile. No installed images or dependency trees were published. This is a new attempt on an existing original task; the historical 83-export denominator and original aggregate counts are unchanged.

Runtime snapshot: `hf://buckets/open-athena/biotasks/research/39-recorded-bootstrap/2026-10-24/94e53ca758799a7b28f7b19b7409c42f68d2a5b1c307355467a823e11d85edeb`.

Final summary/source snapshot: `hf://buckets/open-athena/biotasks/research/39-recorded-bootstrap/2026-10-24/e1f4b248a28a35b679df3c34b0f96bfc0cd57fe64e2f251e498f9ff2697bbe48`.

The first final-metadata scan rejected its own scanner source literals before publication. The raw eligibility guard stayed unchanged; the exact scanner source remains in Git with a hash pointer, and the curation note is preserved. #40 is the separately filed Scanpy transfer question; it has no runtime admission yet.
