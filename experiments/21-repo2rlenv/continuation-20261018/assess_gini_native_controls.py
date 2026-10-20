"""Post-run manual assessment of one unchanged automatic Gini task.

The original export must match its already published asset hashes. Separate
control copies vary only the learner solution; no result goes back to an author.
"""

import json
import sys
from pathlib import Path

import run_authored_native_controls as controls


IDENTIFIER = "808efa9c59c6f356358f"
PROFILE = {
    "recipe": "swe_flow",
    "source": "skbio/diversity/alpha/_gini.py",
    "function": "gini_index",
    "negative_bodies": {
        "incorrect_constant_zero": "return 0.0",
        "incorrect_accepts_unknown_method": (
            "data = _validate_counts_vector(data, cast_int=False)\n"
            "if method not in ('rectangles', 'trapezoids'):\n"
            "    method = 'rectangles'\n"
            "area = _lorenz_curve_integrator(_lorenz_curve(data), method)\n"
            "return max(0.0, 1.0 - 2.0 * area)"
        ),
    },
}


def alternative_source(source, profile):
    assert profile == PROFILE
    return controls.replace_body(
        source, "gini_index",
        "values = _validate_counts_vector(data, cast_int=False)\n"
        "area = _lorenz_curve_integrator(_lorenz_curve(values), method)\n"
        "score = 1.0 - 2.0 * area\n"
        "return float(score) if score > 0.0 else 0.0",
    )


def main():
    inputs = Path(sys.argv[sys.argv.index("--inputs") + 1])
    manifest = json.loads((inputs / "manifest.json").read_text())
    assert manifest["candidate_id"] == IDENTIFIER
    assert manifest["manual_assessment_only"] and not manifest["feedback_to_author"]
    original_prepare = controls.prepare_cases

    def checked_prepare(task, output, identifier, profile):
        assert identifier == IDENTIFIER
        assert controls.assets(task) == manifest["original_published_task_assets"]
        return original_prepare(task, output, identifier, profile)

    controls.PROFILES = {IDENTIFIER: PROFILE}
    controls.alternative_source = alternative_source
    controls.prepare_cases = checked_prepare
    controls.main()


if __name__ == "__main__":
    main()
