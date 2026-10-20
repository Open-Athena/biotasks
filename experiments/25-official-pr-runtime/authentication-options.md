# GitHub authentication precedents

Inspected on 2026-10-20; no credential values were read or copied.

Repo2RLEnv at `27d04ee8203cd5b2f20c3997d13836e5f5b64238` documents
`gh auth login` in its quickstart. Its `auth.py` supports an explicit
`repo.auth_token_env`, then a CLI token lookup, then `GITHUB_TOKEN`.
For this experiment, use an explicitly supplied environment credential and
disable CLI token extraction with the official `auth.use_gh_cli` setting.
This is configuration, not a source patch.

The inspected Marin checkout at
`24aa43cea9a508449d4c9094cb3877e6e43e0f67` contains these precedents:

- `.github/workflows/iris-smoke-coreweave.yaml` supplies the automatically
  issued Actions token as `GH_TOKEN` for GitHub status API calls. This is
  authentication on the CI runner, not evidence that TRC tasks inherit it.
- `.github/workflows/ops-native-package-dependencies.yaml` uses
  `actions/create-github-app-token` and supplies its output as `GH_TOKEN`.
  That integration has its own repository scope and secrets; its existence
  does not authorize reusing those credentials for this experiment.
- `scripts/pm/itemize_experiment_issues.py` takes `GITHUB_TOKEN` from its
  environment rather than discovering a shared remote credential.

These examples support explicit credential injection as the standard
automation pattern. They do not establish an available credential for #25.
For this public-read pilot, a short-lived fine-grained personal token with
public read-only access is the simplest proposed setup, supplied through a
user-approved secret location. A maintained organization integration can use
a GitHub App instead. Do not create a new integration merely to run this pilot.

References:

- https://github.com/huggingface/Repo2RLEnv/blob/27d04ee8203cd5b2f20c3997d13836e5f5b64238/README.md
- https://github.com/huggingface/Repo2RLEnv/blob/27d04ee8203cd5b2f20c3997d13836e5f5b64238/src/repo2rlenv/auth.py
- https://cli.github.com/manual/gh_auth_login
- https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens
