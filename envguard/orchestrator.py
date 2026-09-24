from .models import EnvironmentSpec, OrchestrationReport
from .validator import validate_environment
from .repair import repair_environment
from .readiness import evaluate_readiness

def orchestrate(payload: dict, live_checks: bool = False, auto_repair: bool = True) -> OrchestrationReport:
    validation = validate_environment(payload)
    repaired = None
    candidate = payload

    if not validation.valid and auto_repair:
        candidate, actions = repair_environment(payload)
        repaired = candidate
        validation = validate_environment(candidate)
        if actions:
            candidate.setdefault("metadata", {})["repair_actions"] = " | ".join(actions)

    if validation.valid:
        env = EnvironmentSpec.model_validate(candidate)
        readiness = evaluate_readiness(env, live_checks=live_checks)
        recommendation = (
            "Environment is ready for test execution."
            if readiness.ready
            else "Environment is not ready; resolve failed readiness checks before test execution."
        )
    else:
        readiness = None
        recommendation = "Environment definition is invalid; resolve schema/data-quality errors first."

    return OrchestrationReport(
        validation=validation,
        repaired_environment=repaired,
        readiness=readiness,
        recommendation=recommendation,
    )
