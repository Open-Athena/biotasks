"""Recheck the final recorded review without new model or scientific execution."""

import json
import time

from grading_protocol import (
    Grader,
    Review,
    check_review_asset_hints,
    check_review_scientific_admission,
    check_review_source_coverage,
)
from probe_coverage import unexercised_scientific_checks


def recorded_review_context(grading, inputs):
    if "review_evidence" not in inputs:
        return inputs
    from review_packet import ReviewPacket

    packet = ReviewPacket.open_recorded(
        grading / "review-inspection/review-packets",
        inputs["review_evidence"],
        deadline=time.time() + 60,
    )
    original = packet.reconstruct()
    inline = {key: value for key, value in inputs.items() if key != "review_evidence"}
    if inline != {
        key: value for key, value in original.items() if key in ReviewPacket.INLINE_FIELDS
    }:
        raise ValueError("Inline review inputs differ from their recorded packet")
    return original


def check_final_review(grading):
    def read(path):
        return json.loads(path.read_text())

    candidate = read(grading / "final-candidate.json")
    review = Review.model_validate(
        read(
            grading
            / ("review-repair.json" if (grading / "review-repair.json").exists() else "review.json")
        )
    )
    if review.decision != "accept_for_packaging" or review.issues:
        raise ValueError("Release requires an accepting final review without issues")
    check_review_source_coverage(review)
    # A repair worker may have several submission reviews. Bind the final review
    # to its recorded response and exact candidate, not to the first input file.
    matched = []
    for path in grading.glob("review*/input.json"):
        artifact = path.parent / "artifact-stage/artifact.json"
        if not artifact.is_file():
            continue
        observed = Review.model_validate(read(artifact)["artifact"])
        if observed == review:
            inputs = recorded_review_context(grading, read(path))
            if inputs["candidate"] == candidate:
                matched.append(inputs)
    if not matched:
        raise ValueError("Final review is not bound to a recorded input and exact candidate")
    for inputs in matched:
        check_review_scientific_admission(review, inputs["artifact_interface"]["output_paths"])
        check_review_asset_hints(review, inputs["asset_value_hints"]["findings"])
    controls = read(grading / "final-controls.json")
    if unexercised_scientific_checks(Grader.model_validate(candidate), controls):
        raise ValueError("Every scientific check needs an executed scientific negative")
    return review
