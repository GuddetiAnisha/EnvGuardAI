import re
from difflib import SequenceMatcher
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


class RequirementSpec(BaseModel):
    requirement_id: str = Field(min_length=2)
    parameter: str = Field(min_length=1)
    operator: Literal["eq", "le", "lt", "ge", "gt", "between", "contains", "regex"]
    expected: Any
    unit: Optional[str] = None
    tolerance: float = Field(default=0.0, ge=0.0)
    source_document: str = Field(min_length=1)
    source_section: Optional[str] = None
    description: Optional[str] = None


class ProductionTestResult(BaseModel):
    test_id: str = Field(min_length=1)
    parameter: str = Field(min_length=1)
    value: Any
    unit: Optional[str] = None
    status: Optional[str] = None
    metadata: dict[str, str] = {}


class RequirementMatch(BaseModel):
    requirement_id: str
    test_id: Optional[str]
    match_method: Literal["exact", "similarity", "unmatched"]
    match_score: float = Field(ge=0.0, le=1.0)
    normalized_requirement_parameter: str
    normalized_test_parameter: Optional[str] = None


class VerificationFinding(BaseModel):
    requirement_id: str
    test_id: Optional[str]
    parameter: str
    expected: Any
    actual: Any = None
    unit: Optional[str] = None
    result: Literal["pass", "deviation", "missing_result", "unit_mismatch", "error"]
    deviation: Optional[float] = None
    message: str
    source_document: str
    source_section: Optional[str] = None
    traceability_ref: str
    match_method: str
    match_score: float


class ProductionVerificationReport(BaseModel):
    total_requirements: int
    passed: int
    deviations: int
    missing_results: int
    unit_mismatches: int
    detection_rate: float
    findings: list[VerificationFinding]
    summary: str


def _normalize_name(value: str) -> str:
    value = value.lower().strip()
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def _similarity(a: str, b: str) -> float:
    na, nb = _normalize_name(a), _normalize_name(b)
    if not na or not nb:
        return 0.0
    if na == nb:
        return 1.0
    a_tokens, b_tokens = set(na.split()), set(nb.split())
    token_score = len(a_tokens & b_tokens) / max(1, len(a_tokens | b_tokens))
    seq_score = SequenceMatcher(None, na, nb).ratio()
    return 0.6 * token_score + 0.4 * seq_score


def match_requirement(
    requirement: RequirementSpec,
    results: list[ProductionTestResult],
    similarity_threshold: float = 0.62,
) -> RequirementMatch:
    target = _normalize_name(requirement.parameter)

    for result in results:
        if _normalize_name(result.parameter) == target:
            return RequirementMatch(
                requirement_id=requirement.requirement_id,
                test_id=result.test_id,
                match_method="exact",
                match_score=1.0,
                normalized_requirement_parameter=target,
                normalized_test_parameter=_normalize_name(result.parameter),
            )

    best_result = None
    best_score = 0.0
    for result in results:
        score = _similarity(requirement.parameter, result.parameter)
        if score > best_score:
            best_score = score
            best_result = result

    if best_result is not None and best_score >= similarity_threshold:
        return RequirementMatch(
            requirement_id=requirement.requirement_id,
            test_id=best_result.test_id,
            match_method="similarity",
            match_score=round(best_score, 4),
            normalized_requirement_parameter=target,
            normalized_test_parameter=_normalize_name(best_result.parameter),
        )

    return RequirementMatch(
        requirement_id=requirement.requirement_id,
        test_id=None,
        match_method="unmatched",
        match_score=round(best_score, 4),
        normalized_requirement_parameter=target,
        normalized_test_parameter=None,
    )


def _to_number(value: Any) -> float:
    if isinstance(value, bool):
        raise ValueError("Boolean is not a numeric measurement.")
    return float(value)


def _evaluate(requirement: RequirementSpec, actual: Any) -> tuple[bool, Optional[float], str]:
    op = requirement.operator

    if op == "contains":
        ok = str(requirement.expected).lower() in str(actual).lower()
        return ok, None, "substring check"

    if op == "regex":
        ok = re.search(str(requirement.expected), str(actual)) is not None
        return ok, None, "regular-expression check"

    value = _to_number(actual)

    if op == "between":
        if not isinstance(requirement.expected, (list, tuple)) or len(requirement.expected) != 2:
            raise ValueError("'between' expects [min, max].")
        low, high = map(float, requirement.expected)
        ok = low - requirement.tolerance <= value <= high + requirement.tolerance
        deviation = 0.0 if ok else min(abs(value - low), abs(value - high))
        return ok, deviation, f"expected between {low} and {high}"

    expected = _to_number(requirement.expected)
    tol = requirement.tolerance

    if op == "eq":
        deviation = abs(value - expected)
        return deviation <= tol, deviation, f"expected {expected} +/- {tol}"
    if op == "le":
        return value <= expected + tol, max(0.0, value - expected), f"expected <= {expected}"
    if op == "lt":
        return value < expected + tol, max(0.0, value - expected), f"expected < {expected}"
    if op == "ge":
        return value >= expected - tol, max(0.0, expected - value), f"expected >= {expected}"
    if op == "gt":
        return value > expected - tol, max(0.0, expected - value), f"expected > {expected}"

    raise ValueError(f"Unsupported operator: {op}")


def verify_production_results(
    requirements: list[RequirementSpec],
    results: list[ProductionTestResult],
    similarity_threshold: float = 0.62,
) -> ProductionVerificationReport:
    by_id = {r.test_id: r for r in results}
    findings: list[VerificationFinding] = []

    for requirement in requirements:
        match = match_requirement(requirement, results, similarity_threshold)
        trace = requirement.source_document
        if requirement.source_section:
            trace += f" :: {requirement.source_section}"
        trace += f" :: {requirement.requirement_id}"

        if not match.test_id:
            findings.append(
                VerificationFinding(
                    requirement_id=requirement.requirement_id,
                    test_id=None,
                    parameter=requirement.parameter,
                    expected=requirement.expected,
                    actual=None,
                    unit=requirement.unit,
                    result="missing_result",
                    message="No sufficiently similar production test result was found.",
                    source_document=requirement.source_document,
                    source_section=requirement.source_section,
                    traceability_ref=trace,
                    match_method=match.match_method,
                    match_score=match.match_score,
                )
            )
            continue

        actual_result = by_id[match.test_id]

        if (
            requirement.unit
            and actual_result.unit
            and requirement.unit.strip().lower() != actual_result.unit.strip().lower()
        ):
            findings.append(
                VerificationFinding(
                    requirement_id=requirement.requirement_id,
                    test_id=actual_result.test_id,
                    parameter=requirement.parameter,
                    expected=requirement.expected,
                    actual=actual_result.value,
                    unit=actual_result.unit,
                    result="unit_mismatch",
                    message=f"Requirement unit '{requirement.unit}' does not match test-result unit '{actual_result.unit}'.",
                    source_document=requirement.source_document,
                    source_section=requirement.source_section,
                    traceability_ref=trace,
                    match_method=match.match_method,
                    match_score=match.match_score,
                )
            )
            continue

        try:
            ok, deviation, check_description = _evaluate(requirement, actual_result.value)
            status = "pass" if ok else "deviation"
            message = (
                f"PASS: {check_description}."
                if ok
                else f"DEVIATION: {check_description}; observed {actual_result.value}."
            )
        except Exception as exc:
            status = "error"
            deviation = None
            message = f"Verification error: {exc}"

        findings.append(
            VerificationFinding(
                requirement_id=requirement.requirement_id,
                test_id=actual_result.test_id,
                parameter=requirement.parameter,
                expected=requirement.expected,
                actual=actual_result.value,
                unit=requirement.unit or actual_result.unit,
                result=status,
                deviation=deviation,
                message=message,
                source_document=requirement.source_document,
                source_section=requirement.source_section,
                traceability_ref=trace,
                match_method=match.match_method,
                match_score=match.match_score,
            )
        )

    passed = sum(f.result == "pass" for f in findings)
    deviations = sum(f.result == "deviation" for f in findings)
    missing = sum(f.result == "missing_result" for f in findings)
    unit_mismatches = sum(f.result == "unit_mismatch" for f in findings)
    evaluated = max(1, len(findings))
    detection_rate = round((deviations + missing + unit_mismatches) / evaluated, 4)

    summary = (
        f"Verified {len(requirements)} requirements: {passed} passed, "
        f"{deviations} deviations, {missing} missing results, "
        f"{unit_mismatches} unit mismatches."
    )

    return ProductionVerificationReport(
        total_requirements=len(requirements),
        passed=passed,
        deviations=deviations,
        missing_results=missing,
        unit_mismatches=unit_mismatches,
        detection_rate=detection_rate,
        findings=findings,
        summary=summary,
    )
