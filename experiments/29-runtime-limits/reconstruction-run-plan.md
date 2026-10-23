# Matchms reconstruction attempt 001

Use existing reserved TRC CPU capacity only, one job with 4 allocated CPUs, 16 GiB RAM/disk and a 2,400-second wall limit (at most 2.667 allocated CPU-hours). This consumes part of the #29 32 allocated CPU-hour proposed first-stage bound; it is not an additional allowance. No model calls, project credentials, GitHub authentication or new capacity. One attempt, no automatic retries.

Fetch the original public Matchms commit anonymously. Build its exact saved reconstruction recipe with one infrastructure-only ownership LABEL inserted immediately after FROM. Preserve all base/COPY/RUN instructions. Legacy Docker build has 1.5 CPU and 6 GiB limits and a 1,800-second deadline. No recipe/test fixes. The label permits narrow cleanup of owned build containers/intermediates.

Keep an owned successful image on its recorded worker only for the pending controls; record image identity and reconstruction drift. Remove after controls/archive or investigation termination. Remove owned containers and local clone/tools at completion. Retain private build log plus SHA and result in Iris output storage; public findings exclude raw biological content. Failure stops this reconstruction attempt rather than launching repairs. This stage does not execute controls or establish task recovery.
