# Noninteractive GitHub authentication

The pipeline needs public GitHub API reads through the upstream `gh` client.
Use a machine credential supplied to the launcher as `GH_TOKEN`, then passed only
to the trusted controller's environment. `gh` supports this directly; no browser
login, `gh auth token` extraction, credential-file copying or upstream change is
needed. The launcher fails before submission if the credential is missing.

Keep `GITHUB_TOKEN` unset and the unchanged config's `auth.use_gh_cli=false` so
upstream's public clone path does not resolve/embed a credential in repository
URLs. Target repository containers receive neither the GitHub nor OpenRouter
credential. Authentication failures stop the run before any native model call.

The user selected a new dedicated public-read credential. The existing CI
credential is not authorized for this pipeline and its value has not been read.
Create a fine-grained token with the user's account as resource owner, public
repositories only, no additional permissions, and a 90-day expiration. GitHub
documents that fine-grained tokens include read-only access to public repositories.
The one-time `store_github_token.py --output <private-path>` helper accepts hidden
terminal input and saves it outside the repository with mode 0600 in an existing
0700 directory. It refuses piped input and existing destinations. The private
locator stays outside public evidence. Subsequent launches load that dedicated
file into GH_TOKEN; no browser login is needed until expiration or revocation.
No value is printed or included in commands, logs, source or run artifacts.
Credential creation and actual API access remain unvalidated until user setup.

References: [headless gh authentication](https://cli.github.com/manual/gh_auth_login)
and [GitHub token permissions](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens).

This replaces authentication plumbing only. All native input configurations,
source, prompts/parser, model settings, budgets and Docker limits retain the
recorded comparison values. No native code or per-repository environment is
repaired. The initial browser-auth submission was stopped, made no model calls,
and is retained separately from subsequent attempts.
