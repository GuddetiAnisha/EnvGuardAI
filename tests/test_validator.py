from envguard.validator import validate_environment
from envguard.repair import repair_environment
from envguard.orchestrator import orchestrate

def valid_payload():
    return {
        "environment_name": "integration-demo",
        "environment_type": "integration",
        "namespace": "demo",
        "services": [
            {
                "name": "api",
                "image": "demo/api:1.0",
                "port": 8080,
                "resources": {"cpu": 0.5, "memory_mb": 256, "replicas": 1},
            },
            {
                "name": "worker",
                "image": "demo/worker:1.0",
                "port": 8081,
                "resources": {"cpu": 0.5, "memory_mb": 256, "replicas": 1},
            },
        ],
        "database": {
            "engine": "postgres",
            "host": "postgres",
            "port": 5432,
            "persistent_storage_gb": 2,
        },
    }

def test_valid_environment_passes():
    result = validate_environment(valid_payload())
    assert result.valid is True
    assert result.quality_score >= 90

def test_invalid_environment_fails():
    payload = {"environment_name": "x", "environment_type": "integration", "namespace": "n", "services": []}
    result = validate_environment(payload)
    assert result.valid is False
    assert result.issues

def test_repair_adds_defaults():
    repaired, actions = repair_environment({"services": [{"name": "api", "image": "demo/api"}]})
    assert repaired["environment_type"] == "integration"
    assert repaired["services"][0]["image"].endswith(":latest")
    assert actions

def test_orchestration_produces_readiness():
    report = orchestrate(valid_payload(), live_checks=False)
    assert report.validation.valid is True
    assert report.readiness is not None
    assert report.readiness.ready is True
