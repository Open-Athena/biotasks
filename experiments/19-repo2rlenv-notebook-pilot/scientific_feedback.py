"""Carry validated GLM scientific failures into upstream's bounded repair loop."""

from pathlib import Path

from fidelity import Assessment, validate_assessment
from repo2rlenv.execution.lifecycle import save_record
from repo2rlenv.quality.loop.artifacts import task_identity
from repo2rlenv.quality.loop.models import Citation, Issue
from repo2rlenv.quality.loop.runner import QualityLoop


class ScientificFeedbackLoop(QualityLoop):
    def set_scientific_feedback(self, feedback: dict):
        assessment = Assessment.model_validate(feedback["assessment"])
        validate_assessment(assessment, feedback["documents"])
        self.scientific_feedback = feedback

    def _review(self, task, trials, key, **kwargs):
        review, context = super()._review(task, trials, key, **kwargs)
        if getattr(self, "audit_schema", False):
            from schema_audit import audit

            review = review.model_copy(
                update={"issues": [*review.issues, *audit(self, task, context, key)]}
            )
        feedback = getattr(self, "scientific_feedback", None)
        if feedback is None or task_identity(task) != feedback["bundle_hash"]:
            return review, context
        issues = []
        for finding in Assessment.model_validate(feedback["assessment"]).findings:
            if finding.verdict != "fail":
                continue
            evidence = []
            for citation in finding.citations:
                if not citation.document.startswith("task/"):
                    continue
                name = citation.document.removeprefix("task/")
                path = Path(name)
                if path.is_absolute() or ".." in path.parts:
                    raise ValueError("Unsafe scientific feedback citation")
                original = feedback["documents"][citation.document]
                if (task / path).read_text() != original:
                    raise ValueError("Scientific feedback source no longer matches task")
                evidence.append(Citation(path=name, quote=original.splitlines()[citation.line - 1]))
            if not evidence:
                raise ValueError("Failed scientific finding has no task-bound evidence")
            issues.append(
                Issue(
                    category="verifier",
                    severity="blocking",
                    problem=finding.explanation,
                    repair="Resolve this failed scientific review finding through a grounded repair; preserve the methodology and semantic controls.",
                    evidence=evidence,
                )
            )
        # Keep raw upstream review and scientific assessment intact. This derived
        # record only combines their judgments; it never edits candidate content.
        result = review.model_copy(update={"issues": [*review.issues, *issues]})
        save_record(
            self.directory / "scientific-feedback" / f"{key}.json",
            {"bundle_hash": task_identity(task), "review": result.model_dump(mode="json")},
        )
        return result, context
