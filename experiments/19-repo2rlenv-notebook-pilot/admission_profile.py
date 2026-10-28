"""Versioned admission requirements frozen into new task bundle identities."""

import tomllib

NATIVE_REVIEW_PROFILE = "biotasks-native-contract-v1"


def task_review_profile(task):
    with (task / "task.toml").open("rb") as stream:
        metadata = tomllib.load(stream).get("metadata", {}).get("repo2env", {})
    profile = metadata.get("native_review_profile")
    if profile is not None and profile != NATIVE_REVIEW_PROFILE:
        raise ValueError("Unknown native contract-review profile")
    return profile
