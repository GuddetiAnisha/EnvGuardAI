from fastapi import FastAPI
from pydantic import BaseModel
from envguard.validator import validate_environment
from envguard.repair import repair_environment
from envguard.orchestrator import orchestrate

app = FastAPI(title="EnvGuardAI", version="1.0.0")

class Payload(BaseModel):
    environment: dict
    live_checks: bool = False
    auto_repair: bool = True

@app.get("/health")
def health():
    return {"status": "ok", "service": "envguardai"}

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
