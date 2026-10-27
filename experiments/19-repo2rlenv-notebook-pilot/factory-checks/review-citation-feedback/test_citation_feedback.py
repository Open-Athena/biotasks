"""Citation repair diagnostics keep the exact-text and schema acceptance gates."""

import ast
import copy
import subprocess
from pathlib import Path

import pytest
from specification_protocol import SpecificationReview, validate_specification_review

BASELINE = "c97ff1b2"
SOURCE = "experiments/19-repo2rlenv-notebook-pilot/specification_protocol.py"


def context():
    return {
        "evidence_text": {
            "source.py": 'first line\nsecond line with "quotes"\n',
            "metadata.json": '{\n  "rows": 5\n}',
            "proposal/task_brief": "Compute the named quantity.",
        }
    }


def review(path="source.py", quote="first line"):
    return {
        "disposition": "revise",
        "assessment": "A scientific definition needs correction.",
        "findings": [
            {
                "problem": "A consequential definition is unsupported.",
                "evidence": [{"path": path, "quote": quote}],
                "required_change": "Correct the definition using recorded evidence.",
            }
        ],
    }


def test_quote_failure_names_the_exact_finding_and_citation_without_accepting_it():
    value = review()
    value["findings"].append(copy.deepcopy(value["findings"][0]))
    value["findings"][1]["evidence"].append({"path": "source.py", "quote": "first ... line"})
    with pytest.raises(ValueError) as error:
        validate_specification_review(value, context())
    text = str(error.value)
    assert "findings[1].evidence[1]" in text
    assert 'evidence_text["source.py"]' in text and '"first ... line"' in text
    assert "after JSON decoding" in text and "without hiding a real finding" in text
    value["findings"][1]["evidence"][1]["quote"] = "first line"
    assert validate_specification_review(value, context()).disposition == "revise"


def test_unavailable_path_lists_actual_map_keys_without_creating_evidence():
    evidence = context()
    original = copy.deepcopy(evidence)
    with pytest.raises(ValueError) as error:
        validate_specification_review(review(path="new-tool-result.txt"), evidence)
    text = str(error.value)
    assert "findings[0].evidence[0]" in text
    assert '"new-tool-result.txt"' in text and '"proposal/task_brief"' in text
    assert evidence == original


def test_json_encoded_findings_are_still_rejected_not_silently_unwrapped():
    value = review()
    value["findings"] = "[]"
    with pytest.raises(ValueError, match="valid list"):
        validate_specification_review(value, context())


def test_actual_previous_validator_has_the_same_acceptance_on_citation_scenarios():
    repository = Path(__file__).resolve().parents[4]
    raw = subprocess.check_output(["git", "show", BASELINE + ":" + SOURCE], cwd=repository)
    function = next(
        node
        for node in ast.parse(raw).body
        if isinstance(node, ast.FunctionDef) and node.name == "validate_specification_review"
    )
    scope = {"SpecificationReview": SpecificationReview}
    exec(compile(ast.Module(body=[function], type_ignores=[]), SOURCE, "exec"), scope)
    previous = scope["validate_specification_review"]
    paths = ["source.py", "metadata.json", "proposal/task_brief", "missing.txt", " "]
    quotes = [
        "first line",
        "second line",
        "first ... line",
        "first line\nsecond line",
        "first line\\nsecond line",
        '"rows": 5',
        "Compute the named quantity.",
        "invented",
        " ",
        "",
    ]
    count = 0
    for disposition in ["ready", "revise", "reject"]:
        for path in paths:
            for quote in quotes:
                for multiple in [False, True]:
                    value = review(path, quote)
                    value["disposition"] = disposition
                    if multiple:
                        value["findings"].insert(0, review()["findings"][0])
                    observed = []
                    for validate in [previous, validate_specification_review]:
                        try:
                            result = validate(value, context())
                        except ValueError:
                            observed.append(False)
                        else:
                            observed.append(result.model_dump())
                    assert observed[0] == observed[1], (disposition, path, quote, multiple)
                    count += 1
    assert count == 300
