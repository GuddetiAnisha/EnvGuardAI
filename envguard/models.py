from typing import Literal, Optional
from pydantic import BaseModel, Field, model_validator

class ResourceSpec(BaseModel):
    cpu: float = Field(gt=0, description="CPU cores")
    memory_mb: int = Field(gt=0)
    replicas: int = Field(ge=1, le=50)

class ServiceSpec(BaseModel):
    name: str = Field(min_length=2)
    image: str = Field(min_length=3)
    port: int = Field(ge=1, le=65535)
    health_path: str = "/health"
    resources: ResourceSpec
    required: bool = True

class DatabaseSpec(BaseModel):
    engine: Literal["postgres", "mysql", "sqlite"] = "postgres"
    host: str = "postgres"
    port: int = 5432
    persistent_storage_gb: int = Field(default=2, ge=1)
    required: bool = True

class EnvironmentSpec(BaseModel):
    environment_name: str = Field(min_length=3)
    environment_type: Literal["integration", "system", "staging", "performance"]
    namespace: str = Field(min_length=2)
    services: list[ServiceSpec]
    database: Optional[DatabaseSpec] = None
    required_secrets: list[str] = []
    metadata: dict[str, str] = {}
    auto_repair: bool = False

    @model_validator(mode="after")
    def unique_services(self):
        names = [s.name for s in self.services]
        if len(names) != len(set(names)):
            raise ValueError("Service names must be unique.")
        if not self.services:
            raise ValueError("At least one service is required.")
        return self

class ValidationIssue(BaseModel):
    severity: Literal["error", "warning", "info"]
    field: str
    message: str
    suggested_fix: Optional[str] = None

class ValidationResult(BaseModel):
    valid: bool
    quality_score: float
    issues: list[ValidationIssue]
    normalized_environment: dict | None = None

class ReadinessCheck(BaseModel):
    component: str
    check: str
    status: Literal["pass", "fail", "warning"]
    details: str

class ReadinessResult(BaseModel):
    ready: bool
    score: float
    checks: list[ReadinessCheck]

class OrchestrationReport(BaseModel):
    validation: ValidationResult
    repaired_environment: dict | None = None
    readiness: ReadinessResult | None = None
    recommendation: str
