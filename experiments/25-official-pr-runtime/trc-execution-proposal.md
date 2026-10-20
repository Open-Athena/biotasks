# TRC execution arrangement for the official pipeline

Status: resource-only wrapper approved by the user on 2026-10-20; native run
not launched. Upstream source remains unchanged.

Use one existing reserved TRC worker with a four-CPU, 16-GiB reservation.
Run the controller in a container capped at one CPU and 4 GiB. Give it the
existing Docker socket so the official pipeline can launch its test containers.
Use a run-specific Docker CLI wrapper only for container creation: append
`--cpus=1.5 --memory=6g --memory-swap=6g`, a run ownership label, and the
worker's existing `iris-egress` network. Permit at most two simultaneously
running pipeline containers. Upstream's fresh-image bootstrap check runs
while its original bootstrap container is still alive, so two are necessary.
The controller plus those two containers have caps totaling four CPUs and
16 GiB. Shared Docker daemon overhead and image-cache space are separate;
record them as an infrastructure limitation, not task memory measurements.

For example, the upstream command:

```text
docker run -d --platform linux/amd64 --name r2e-... -w /workspace IMAGE sleep infinity
```

would execute as:

```text
docker run --cpus=1.5 --memory=6g --memory-swap=6g --network=iris-egress --label biotasks.run=RUN_ID -d --platform linux/amd64 --name r2e-... -w /workspace IMAGE sleep infinity
```

The wrapper must reject conflicting resource/network options, serialize the
creation-count check, and fail rather than exceed two running task containers.
All other native Docker operations retain their original arguments. Pin a
Docker client compatible with the host daemon; do not repeat #24's custom
Docker commit transport adaptation. The wrapper is an infrastructure
adaptation and must be reported even though it does not patch Repo2RLEnv.
Resource caps can affect timeouts or out-of-memory outcomes; retain them in
the interpretation of any failure.

Run `gh auth login --hostname github.com --git-protocol https --web` inside
the persistent controller container. The user authorizes the displayed code
in their browser. The controller's private authentication directory stays
there, is excluded from artifacts and is removed with the container. Use
official `auth.use_gh_cli=false` to prevent upstream from extracting a token;
normal `gh` read commands can use their own authenticated session. Public
Git clones need no credential. Do not transfer existing local credentials.

Inject the approved OpenRouter key into the controller process environment,
not the repository containers. Use the native model setting
`openrouter/z-ai/glm-5.3`, no fallback, 20 bootstrap turns, the native
2,048-output-token request and a $5 estimated threshold per repository.
No separate model-generation compatibility probe is permitted.

Run the five recorded date windows through the official CLI with a shared
repository bootstrap cache. Do not restart failed bootstrap attempts. Preserve
native outcomes for the five comparison PRs and 11 additional same-day inputs
separately. If pipeline assumptions fail, retain the failure; do not repair
source, tests, prompts or package installation externally.

Image builds and Harbor base/reference controls require their own bounded
execution commands to be checkpointed before that stage. Export alone is not
a verified task. Do not release task images or publish credentials.

Use a supervisor deadline and ownership labels to remove only this run's
containers/images, then verify artifact readback and cleanup. The supervisor
must be ready before authentication begins so the login and generated images
can stay on the same executor throughout the run.
