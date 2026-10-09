# Harness source inspection — 2026-10-09

This is static inspection, not an installed-runtime test or proof of endpoint connectivity.

## ZCode

Pin: `zai-org/ZCode@29628c9acdb81b703bbd4080c207a0e7ce5e276e`.

- [`arguments.ts`](https://github.com/zai-org/ZCode/blob/29628c9acdb81b703bbd4080c207a0e7ce5e276e/apps/zcode-cli/packages/cli/src/arguments.ts) accepts `-p`/`--prompt`, `--cwd`, `--output-format` and permission mode. Do not assume Claude Code CLI flags work unchanged.
- [`prompt-command.ts`](https://github.com/zai-org/ZCode/blob/29628c9acdb81b703bbd4080c207a0e7ce5e276e/apps/zcode-cli/packages/cli/src/prompt-command.ts) implements headless `stream-json` events and a terminal result record. This offers a concrete trace-capture path to test.
- [`provider-data-schema.ts`](https://github.com/zai-org/ZCode/blob/29628c9acdb81b703bbd4080c207a0e7ce5e276e/packages/provider/src/config/provider-data-schema.ts) supports `openai-chat-completions`, a custom `baseUrl` and API-key access. Exact provider/model selection, auxiliary model routing, context/output settings and compatibility with the selected service require a smoke test.
- [`env-config.adapter.ts`](https://github.com/zai-org/ZCode/blob/29628c9acdb81b703bbd4080c207a0e7ce5e276e/apps/zcode-cli/packages/adapters/src/config/env-config.adapter.ts) has a deliberately small environment-variable surface. Setting arbitrary `ZCODE_API_KEY` or `ZCODE_BASE_URL` variables is not a verified configuration method.

## Harbor / Pi

Pin: `marin-community/harbor@9f7b8b404711445b6022f72ff7e5715eb0d1a316`.

[`pi.py`](https://github.com/marin-community/harbor/blob/9f7b8b404711445b6022f72ff7e5715eb0d1a316/src/harbor/agents/installed/pi.py) supports a custom `api_base`, requires explicit `thinking_format` for that route, configures context/output limits, and executes `pi --print --mode json --no-session` inside the task environment. Endpoint configuration is staged inside that environment. This means a completely disconnected task sandbox would also disconnect this Pi model client unless a separate controlled inference route is provided.

An inference allowlist alone does not establish credential isolation from arbitrary task commands. A protected proxy or host-side Pi tool transport needs investigation, with both model connectivity and task-network denial tested. Do not claim that removing web tools or setting a task flag verifies offline execution. Do not silently replace Pi with Terminus-2.

The pinned `src/harbor/models/task/config.py` re-exports `harbor_config` types; inspect the actual `src/harbor_config/models/task/config.py` before generating launch settings. Effective separate-verifier execution and preservation of timeout artifacts still require runtime checks.
