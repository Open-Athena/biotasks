# Native GLM effort

For subsequent campaigns the user selected **native `high`**, the middle of
GLM-5.3's `low`, `high`, and `max` levels. The same explicit setting is passed
to preparation, setup, specification, construction, scientific validation and
the blind Harbor solver. It adds no token or request-count cap. Non-native
effort aliases are rejected by the campaign profile before execution.

An offline Jinja rendering of the [official public template at a fixed revision](https://huggingface.co/zai-org/GLM-5.3/blob/ba32f8c19c8738e2c57c71798c601d477a7bf844/chat_template.jinja)
maps requested `medium` to `max`, and `high` to `high`. `result.json` records
the template checksum and all four synthetic renders. No model call or cloud
resource was used for this diagnostic.

This does **not** establish the template deployed by the approved endpoint.
Its saved response metadata did not contain a rendered prompt or prompt token
IDs. Existing campaigns 024 and 025 therefore remain **medium requested;
effective served effort unverified**. Their immutable settings, traces, failures
and time limits are unchanged. Do not claim their actual effort was `max`.

The previous ten-input packaging manifest is preserved as packaging evidence.
Its unsubmitted payloads 026–033 are superseded for future submissions. Fresh
campaign configurations 034–043 retain exactly the original ten notebook
sources and task limits, and explicitly request `high`. They are not ten
completed runs; their plan records preparation and submission separately.
