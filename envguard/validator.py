from pydantic import ValidationError
from .models import EnvironmentSpec, ValidationIssue, ValidationResult

def validate_environment(payload: dict) -> ValidationResult:
    issues: list[ValidationIssue] = []
    normalized = None
    try:
        env = EnvironmentSpec.model_validate(payload)
        normalized = env.model_dump()
    except ValidationError as exc:
        for err in exc.errors():
            field = ".".join(str(x) for x in err["loc"])
            issues.append(ValidationIssue(
                severity="error",
                field=field or "root",
                message=err["msg"],
                suggested_fix="Correct the field to satisfy the declared schema.",
            ))
        return ValidationResult(valid=False, quality_score=max(0, 100 - 15 * len(issues)), issues=issues)

    if len(env.services) < 2:
        issues.append(ValidationIssue(
            severity="warning",
            field="services",
            message="Only one service is defined; integration environments usually contain multiple components.",
            suggested_fix="Confirm whether dependent services are missing.",
        ))

    seen_ports: dict[int, str] = {}
    for svc in env.services:
        if svc.port in seen_ports:
            issues.append(ValidationIssue(
                severity="warning",
                field=f"services.{svc.name}.port",
                message=f"Port {svc.port} is also used by {seen_ports[svc.port]}.",
                suggested_fix="Verify whether port reuse is intentional.",
            ))
        else:
            seen_ports[svc.port] = svc.name
        if ":" not in svc.image:
            issues.append(ValidationIssue(
                severity="warning",
                field=f"services.{svc.name}.image",
                message="Container image has no explicit tag.",
                suggested_fix="Pin an immutable or versioned image tag.",
            ))
        if svc.resources.memory_mb < 128:
            issues.append(ValidationIssue(
                severity="warning",
                field=f"services.{svc.name}.resources.memory_mb",
                message="Memory request is very low for a test service.",
                suggested_fix="Review expected memory consumption.",
            ))

    if env.environment_type in {"integration", "system", "performance"} and env.database is None:
        issues.append(ValidationIssue(
            severity="warning",
            field="database",
            message="No database is configured for a non-trivial test environment.",
            suggested_fix="Confirm that the environment is intentionally stateless.",
        ))

    if not env.required_secrets:
        issues.append(ValidationIssue(
            severity="info",
            field="required_secrets",
            message="No required secrets are declared.",
            suggested_fix="Declare external credentials/secrets if the environment depends on them.",
        ))

    penalties = sum(12 if i.severity == "error" else 5 if i.severity == "warning" else 1 for i in issues)
    score = max(0.0, 100.0 - penalties)
    valid = not any(i.severity == "error" for i in issues)
    return ValidationResult(valid=valid, quality_score=score, issues=issues, normalized_environment=normalized)
