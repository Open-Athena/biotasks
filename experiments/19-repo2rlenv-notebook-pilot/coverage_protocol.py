"""Evidence-grounded endpoint proposals; no grading acceptance is implied."""

from typing import Literal

from pydantic import Field, model_validator
from reference_protocol import StrictModel


class Evidence(StrictModel):
    artifact: str
    location: str = Field(
        min_length=1,
        description="Exact CSV header (or column[N]), exact HDF5 path, or $file for file-level metadata. Must exist in the supplied profile.",
    )
    observation: str = Field(min_length=1)
    status: Literal["observed", "derivable_but_unverified"]


class Endpoint(StrictModel):
    name: str = Field(min_length=1)
    scientific_result: str = Field(min_length=1)
    source_evidence: str = Field(min_length=1)
    reference_evidence: list[Evidence] = Field(min_length=1)
    proposed_representation: str = Field(min_length=1)
    comparison_risks: list[str]
    required_executable_validation: list[str] = Field(min_length=1)


class CoveragePlan(StrictModel):
    disposition: Literal["propose_contract", "reference_work_required", "reject"]
    rationale: str = Field(min_length=1)
    endpoints: list[Endpoint]
    supporting_artifacts: list[str]
    excluded_results_with_reasons: list[str]
    corrections_to_prior_claims: list[str]
    missing_reference_evidence: list[str] = Field(
        description="Defects only, [] if no missing reference evidence is known."
    )
    next_validation: list[str]

    @model_validator(mode="after")
    def ready(self):
        if self.disposition == "propose_contract" and (
            not self.endpoints or self.missing_reference_evidence
        ):
            raise ValueError(
                "A contract proposal needs endpoints and no known missing reference evidence; unresolved grading checks belong in next_validation."
            )
        names = [endpoint.name for endpoint in self.endpoints]
        if len(set(names)) != len(names):
            raise ValueError("Endpoint names must be unique")
        return self


class CoverageReview(StrictModel):
    decision: Literal["approve", "revise", "reject"]
    rationale: str = Field(min_length=1)
    omitted_scientific_endpoints: list[str]
    unsupported_evidence_claims: list[str]
    scientific_scope_changes: list[str]
    remaining_validation: list[str]

    @model_validator(mode="after")
    def ready(self):
        if self.decision == "approve" and any(
            (
                self.omitted_scientific_endpoints,
                self.unsupported_evidence_claims,
                self.scientific_scope_changes,
            )
        ):
            raise ValueError(
                "Approval requires empty defect lists. Put positive findings in rationale; keep actual defects and revise or reject."
            )
        return self


def validate_evidence(plan, observations):
    known = {item["path"]: item for item in observations}
    for endpoint in plan.endpoints:
        for evidence in endpoint.reference_evidence:
            if evidence.artifact not in known:
                raise ValueError("Evidence names an artifact absent from the observed inventory")
            profile = known[evidence.artifact]
            locations = {"$file"}
            locations.update(node["path"] for node in profile.get("nodes", []))
            for column in profile.get("columns", []):
                locations.add(column["name"])
                locations.add(f"column[{column['position']}]")
            if evidence.location not in locations:
                raise ValueError(
                    "Evidence location is absent from the observed artifact profile; cite an exact column name, column[N], HDF5 path or $file."
                )
    if any(path not in known for path in plan.supporting_artifacts):
        raise ValueError("Supporting artifact absent from the observed inventory")
    return plan
