"""Invoke the pinned official CLI once with declared deterministic policies."""

import dataclasses
from contextlib import contextmanager
import functools
import hashlib
import json
import runpy
import sys
import time
from datetime import date
from decimal import Decimal
from pathlib import Path


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def guard_completion(recorder, original, run_budget, price_guard):
    checked = price_guard.wrap(recorder, original, Decimal(run_budget["maximum_usd"]), Decimal(0))

    @functools.wraps(original)
    def forward(*args, **kwargs):
        require(not args and recorder.calls < 20, "Native call count bound reached")
        require(
            kwargs.get("model") == "openrouter/anthropic/claude-sonnet-4.6"
            and kwargs.get("max_tokens") == 2048
            and kwargs.get("temperature") == 0.2
            and kwargs.get("num_retries") == 0,
            "Native model parameters changed",
        )
        require(
            not any(
                kwargs.get(k)
                for k in ("response_format", "tools", "plugins", "reasoning", "tool_choice")
            ),
            "Unexpected paid or formatting option",
        )
        return checked(*args, **kwargs)

    return forward


def check_candidates(values, expected):
    require(
        [dataclasses.asdict(value) for value in values] == expected,
        "Frozen candidate descriptors changed; no wider discovery or replacement",
    )
    return values


@contextmanager
def targeting_policy(family, state):
    name = family.get("targeting_policy")
    require(name in (None, "workspace-python-v1"), "Unknown targeting policy")
    state["targeting_policy"] = name
    if name is None:
        yield
        return
    import python_targeting
    from repo2rlenv.pipelines import pr_runtime

    original = pr_runtime.targeted_test_cmds_for_pr
    candidate = python_targeting.wrap(original)
    pr_runtime.targeted_test_cmds_for_pr = candidate
    try:
        yield
    finally:
        pr_runtime.targeted_test_cmds_for_pr = original
        state["targeting_policy_restored"] = True


def main():
    import cost_guard
    import option_policy
    from observed_cli import Recorder, install_hooks

    recorder = Recorder("/work/native-observations")
    recorder.billing()
    state = {
        "started": time.time(),
        "native_cli_started": False,
        "model_policy": "Original upstream bootstrap only",
        "state": "preflight",
    }
    target = Path("/work/evidence/generation-window.json")

    def save():
        target.write_text(recorder.text(state) + "\n")

    try:
        save()
        source = Path("/work/upstream")
        manifest = json.loads(Path("/work/upstream-source-manifest.json").read_text())
        require(
            manifest["revision"] == "27d04ee8203cd5b2f20c3997d13836e5f5b64238",
            "Unsupported source revision",
        )
        for row in manifest["files"]:
            path = source / row["path"]
            require(
                path.resolve().is_relative_to(source) and path.is_file() and not path.is_symlink(),
                "Unsafe upstream source",
            )
            require(
                hashlib.sha256(path.read_bytes()).hexdigest() == row["sha256"],
                "Installed official source differs",
            )
        config_path = Path("/work/inputs/reference.json")
        config = json.loads(config_path.read_text())
        require(
            config["pipeline"]["name"] == "pr_runtime"
            and config["llm"]
            == {
                "provider": "openrouter",
                "model": "anthropic/claude-sonnet-4.6",
                "api_key_env": "OPENROUTER_API_KEY",
                "fallback": None,
            },
            "Unapproved model/pipeline",
        )
        require(
            config["bootstrap"]
            == {
                "max_iterations": 20,
                "max_seconds": 1800,
                "max_llm_spend_usd": 5.0,
                "cache_dir": "./workspace/bootstrap",
            },
            "Bootstrap settings changed",
        )
        cache = source / "workspace/bootstrap"
        require(not cache.exists() or not any(cache.iterdir()), "Fresh bootstrap cache required")
        expected = json.loads(Path("/work/reference-candidates.json").read_text())
        options = config["pipeline"]["options"]
        require(
            option_policy.matches(options, expected),
            "Frozen listing options changed",
        )
        owner, name = expected["repo"].split("/")
        require(
            config["repo"]["url"] == "https://github.com/" + expected["repo"],
            "Source repository changed",
        )
        from repo2rlenv import github

        before = github.list_merged_prs(
            owner,
            name,
            limit=options["limit"],
            since=date.fromisoformat(options["since"]),
            until=date.fromisoformat(options["until"]),
        )
        check_candidates(before, expected["candidates"])
        state.update(candidate_preflight_verified=True, candidate_count=len(before))
        save()
        install_hooks(recorder)
        observed_listing = github.list_merged_prs

        @functools.wraps(observed_listing)
        def frozen_listing(*args, **kwargs):
            return check_candidates(observed_listing(*args, **kwargs), expected["candidates"])

        github.list_merged_prs = frozen_listing
        import litellm

        budget = json.loads(Path("/work/model-run-budget.json").read_text())
        litellm.completion = guard_completion(recorder, litellm.completion, budget, cost_guard)
        executable = "/work/upstream/.venv/bin/repo2rlenv"
        sys.argv = [
            executable,
            "--no-ui",
            "generate",
            "--config",
            str(config_path),
            "--max-spend-usd",
            "5",
        ]
        family = json.loads(Path("/work/family.json").read_text())
        with targeting_policy(family, state):
            state.update(native_cli_started=True, command=sys.argv, state="native_running")
            save()
            runpy.run_path(executable, run_name="__main__")
            state.update(native_exit_code=0, state="native_returned")
    except SystemExit as error:
        state.update(
            native_exit_code=error.code if isinstance(error.code, int) else 1,
            state="native_returned",
        )
        raise
    except BaseException as error:
        state.update(state="failed", error_type=type(error).__name__)
        raise
    finally:
        recorder.billing()
        state.update(
            finished=time.time(),
            recorded_model_calls=recorder.calls,
            recorded_actual_usd=str(recorder.actual_cost),
            cost_complete=not recorder.cost_unknown,
        )
        save()


if __name__ == "__main__":
    main()
