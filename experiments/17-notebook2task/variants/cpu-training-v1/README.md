# CPU-training variant v1

The two-line [training-policy diff](training-policy.patch) resolves the notebook
adapter's request for trained-model comparison against shared prompts that ban
training. Original SETA snapshots remain unchanged.

The separate [grading contract](grading-contract.md) responds to the observed
GLM draft's unverifiable holdout claims. It fixes the comparison protocol and
requires independent native recomputation. This is a second, substantive change:
it trades open model choice for reproducible analysis grading. This combined
pilot cannot isolate the effects of the policy edit and grading recipe.

Stage plan: GLM revises the earlier cytopathology draft, then generates a package;
parent inspects it and runs CPU reference/negative controls. Generated artifacts
and parent repairs stay separate. No acceptance based solely on an LLM report.
