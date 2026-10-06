# CPU-training recipe pilot

One cytopathology idea revision and one subsequent builder stage through the
existing GLM bulk service. Idea stage: medium reasoning, 16,384 output tokens,
16 requests, ten minutes, 240,000 serialized-context characters, no request
retries. Builder planned ceiling: 24 requests / 15 minutes with the same per-call
output cap. One sequential CPU worker; no new inference deployment or GPU.

Original source inputs and upstream prompt snapshots remain pinned to the earlier
pilot. The combined variant changes training policy and grading recipe, so it is
not a one-variable ablation. Keep raw generated packages immutable. Record any
parent changes before validating on authorized remote CPU capacity. Validate
reference, empty and meaningful wrong submissions, preserving failed attempts.
Stop before any general task release or benchmark scoring claim.
