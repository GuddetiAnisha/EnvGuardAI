from fastapi import FastAPI
from pydantic import BaseModel
from envguard.validator import validate_environment
from envguard.repair import repair_environment
from envguard.orchestrator import orchestrate
from envguard.failure_intelligence import analyze_batch, analyze_failure, self_heal_plan
from envguard.models import FailureRecord

app = FastAPI(title="EnvGuardAI", version="2.0.0")

class Payload(BaseModel):
    environment: dict
    live_checks: bool = False
    auto_repair: bool = True

class FailureBatchPayload(BaseModel):
    failures: list[FailureRecord]

@app.get("/health")
def health():
    return {"status": "ok", "service": "envguardai", "version": "2.0.0"}

@app.post("/validate")
def validate(payload: dict):
    return validate_environment(payload)

@app.post("/repair")
def repair(payload: dict):
    repaired, actions = repair_environment(payload)
    return {"repaired_environment": repaired, "actions": actions}

@app.post("/orchestrate")
def run_orchestration(request: Payload):
    return orchestrate(
        request.environment,
        live_checks=request.live_checks,
        auto_repair=request.auto_repair,
    )

@app.post("/failures/analyze")
def analyze_single_failure(record: FailureRecord):
    analysis = analyze_failure(record)
    return {
        "analysis": analysis,
        "self_heal_plan": self_heal_plan(analysis),
    }

@app.post("/failures/analyze-batch")
def analyze_failure_batch(request: FailureBatchPayload):
    return analyze_batch(request.failures)
