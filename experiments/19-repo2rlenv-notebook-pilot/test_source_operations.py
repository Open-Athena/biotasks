"""Coverage boundaries over synthetic operations; no notebook-specific rules."""

import pytest
from materialization_protocol import Materialization
from source_operations import check_operation_coverage, operation_inventory


def fixture():
    inventory = operation_inventory(
        "small = compare(data[:2])\nlarge = compare(data)\ninteractions = interact(data)\nprint(interactions)\n"
    )
    ids = [item["id"] for item in inventory["operations"]]
    candidate = Materialization(
        disposition="ready",
        instruction="Compare samples and estimate interactions.",
        input_paths=["data.csv"],
        output_paths=["comparisons.csv", "interactions.csv"],
        derive_code="pass",
        oracle_code="pass",
        rationale="Synthetic source",
        operation_coverage=[
            dict(
                operation_ids=[ids[0]],
                role="redundant",
                artifact_paths=[],
                counterpart_id=ids[1],
                rationale="Same compare, state and parameters; first two rows are a projection.",
            ),
            dict(
                operation_ids=[ids[1]],
                role="result",
                artifact_paths=["comparisons.csv"],
                counterpart_id=None,
                rationale="Complete comparison population.",
            ),
            dict(
                operation_ids=[ids[2]],
                role="result",
                artifact_paths=["interactions.csv"],
                counterpart_id=None,
                rationale="Distinct scientific interaction analysis.",
            ),
            dict(
                operation_ids=[ids[3]],
                role="presentation",
                artifact_paths=[],
                counterpart_id=None,
                rationale="Only prints the retained interaction result.",
            ),
        ],
    )
    return inventory, candidate, ids


def test_inventory_keeps_unnamed_overwritten_nested_and_conditional_calls():
    source = "x = analyze(a)\nx = other(a)\nanalyze(b)\nif False:\n    print(analyze(c))\n"
    inventory = operation_inventory(source)
    assert [item["function"] for item in inventory["operations"]] == [
        "analyze",
        "other",
        "analyze",
        "print",
        "analyze",
    ]
    assert len({item["id"] for item in inventory["operations"]}) == 5
    assert inventory == operation_inventory(source)
    assert (
        inventory["source_sha256"]
        != operation_inventory(source + "# new narrative\n")["source_sha256"]
    )


def test_valid_retained_results_and_projection_accounting():
    inventory, candidate, _ = fixture()
    check_operation_coverage(candidate, inventory)
    # This is structural evidence only: the guard does not establish the
    # scientific truth of the worker's same-operation projection claim.


@pytest.mark.parametrize(
    "source",
    [
        "result = load_data(path).summarize().round(2)\n",
        "result = (\n    load_data(path)\n    .summarize()\n    .round(2)\n)\n",
    ],
)
def test_chained_calls_remain_distinct_even_with_the_same_start(source):
    inventory = operation_inventory(source)
    rows = inventory["operations"]
    assert len(rows) == len({row["id"] for row in rows}) == 3
    assert len({(row["line"], row["column"]) for row in rows}) == 1
    assert len({(row["end_line"], row["end_column"]) for row in rows}) == 3
    assert {row["source"].replace("\n", "").replace(" ", "") for row in rows} == {
        "load_data(path)",
        "load_data(path).summarize()",
        "load_data(path).summarize().round(2)",
    }
    assert inventory == operation_inventory(source)


def test_unambiguous_source_call_identifiers_remain_stable():
    rows = operation_inventory("analyze(data)\nshow(data)\n")["operations"]
    assert [row["id"] for row in rows] == ["call-1-0", "call-2-0"]


def test_duplicate_inventory_id_cannot_silently_replace_an_operation():
    inventory, candidate, _ = fixture()
    hidden = dict(inventory["operations"][2], function="hidden", source="hidden(data)")
    inventory["operations"].append(hidden)
    with pytest.raises(ValueError, match="IDs must be distinct"):
        check_operation_coverage(candidate, inventory)


@pytest.mark.parametrize(
    "defect",
    [
        "missing",
        "unknown",
        "duplicate",
        "different_operation",
        "cycle",
        "absent_counterpart",
        "unretained_counterpart",
        "missing_output",
        "unknown_output",
    ],
)
def test_bad_accounting_is_rejected(defect):
    inventory, candidate, ids = fixture()
    if defect == "missing":
        candidate.operation_coverage.pop()
    elif defect == "unknown":
        candidate.operation_coverage[-1].operation_ids = ["not-a-source-call"]
    elif defect == "duplicate":
        candidate.operation_coverage[-1].operation_ids = [ids[0]]
    elif defect == "different_operation":
        candidate.operation_coverage[0].counterpart_id = ids[2]
    elif defect == "cycle":
        candidate.operation_coverage[0].counterpart_id = ids[0]
    elif defect == "absent_counterpart":
        candidate.operation_coverage[0].counterpart_id = "missing"
    elif defect == "unretained_counterpart":
        candidate.operation_coverage[1].role = "support"
        candidate.operation_coverage[1].artifact_paths = []
        candidate.output_paths.remove("comparisons.csv")
    elif defect == "missing_output":
        candidate.output_paths.append("unexplained.csv")
    else:
        candidate.operation_coverage[1].artifact_paths = ["not-requested.csv"]
    with pytest.raises(ValueError):
        check_operation_coverage(candidate, inventory)


def test_explicit_intermediate_has_input_provenance_and_downstream_result():
    inventory, candidate, _ = fixture()
    candidate.input_paths.append("comparisons.csv")
    candidate.output_paths.remove("comparisons.csv")
    candidate.operation_coverage[1].role = "supplied_input"
    check_operation_coverage(candidate, inventory)
    candidate.operation_coverage[1].artifact_paths = ["not-supplied.csv"]
    with pytest.raises(ValueError, match="actual task inputs"):
        check_operation_coverage(candidate, inventory)


def test_legacy_schema_remains_readable_but_new_accounting_is_required():
    inventory, candidate, _ = fixture()
    old = candidate.model_dump(exclude={"operation_coverage"})
    legacy = Materialization.model_validate(old)
    assert legacy.operation_coverage == []
    with pytest.raises(ValueError, match="Missing original"):
        check_operation_coverage(legacy, inventory)
