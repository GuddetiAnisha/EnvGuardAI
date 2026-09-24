# EnvGuardAI

EnvGuardAI is an intelligent software-quality prototype combining:

1. data-quality validation for integration test environments
2. readiness orchestration before test execution
3. failed-test classification and root-cause analysis
4. similarity clustering for recurring failures
5. remediation and guarded self-healing recommendations

It is inspired by the problem areas in Ericsson thesis topics **789574** and **789573**. It contains no Ericsson code, proprietary test logs, or production data.

## Main capabilities

### Environment orchestration

- validates YAML/JSON environment definitions with Pydantic schemas
- scores configuration data quality and reports structured issues
- detects missing, inconsistent or risky environment information
- applies deterministic repair rules and re-validates the result
- checks service, database, secret and health-readiness conditions
- supports optional HTTP/TCP live readiness checks
- exposes orchestration through FastAPI and Streamlit
- includes Docker, Kubernetes manifests, Pytest and GitHub Actions CI

### Failure intelligence

- parses failed test logs and normalizes volatile identifiers
- classifies common failures into:
  - infrastructure
  - configuration
  - dependency
  - flaky-test
  - resource
  - application
  - unknown
- generates probable root causes and confidence scores
- creates stable failure signatures for recurring-pattern tracking
- clusters related failures using TF-IDF and K-Means
- summarizes recurring failure categories across a batch
- generates remediation recommendations
- creates guarded self-healing plans for selected failure types

## Failure-analysis architecture

```text
Failed test executions
        |
        v
 Log normalization
        |
        +----------------------+
        |                      |
        v                      v
Failure classification    TF-IDF vectors
        |                      |
        v                      v
Root-cause hypothesis      K-Means clustering
        |                      |
        +-----------+----------+
                    |
                    v
        Recurring failure patterns
                    |
                    v
        Remediation recommendation
                    |
                    v
          Self-healing planner
                    |
        +-----------+-----------+
        |                       |
    automatic               approval needed
 guarded retry          config/dependency/
                        resource changes
```

The self-healing layer intentionally uses guardrails. Potentially disruptive actions such as resource changes, dependency restoration or configuration modification are recommendations requiring validation or approval rather than unrestricted autonomous execution.

## Quick start

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

pip install -r requirements.txt
python -m pytest -q

uvicorn api:app --reload
```

API documentation:

```text
http://127.0.0.1:8000/docs
```

Dashboard:

```bash
streamlit run app.py
```

## Failure APIs

### Analyse one failure

`POST /failures/analyze`

Example:

```json
{
  "test_name": "payment_api_health",
  "log": "Connection refused while contacting payment-api:8080",
  "environment": "integration-01",
  "retry_count": 1
}
```

Returns:

- failure category
- probable root cause
- confidence
- stable signature
- remediation recommendations
- guarded self-healing plan

### Analyse a batch

`POST /failures/analyze-batch`

Takes a list of failed test records and returns classifications, similarity clusters, recurring-category counts and an overall summary.

A sample dataset is available in `configs/sample_failures.json`.

## Docker

```bash
docker compose up --build
```

## Kubernetes

Update the image in `k8s/deployment.yaml`, then:

```bash
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml
```

## CI/CD

The GitHub Actions workflow installs dependencies and executes the automated test suite on pushes and pull requests.

## CV-safe description

**EnvGuardAI — AI-Driven Test Failure Analysis & Environment Orchestration**  
Python, FastAPI, Scikit-learn, Pydantic, Streamlit, Docker, Kubernetes, Pytest

- Built an intelligent test-automation prototype combining environment data-quality validation, readiness orchestration, failed-test analysis and remediation recommendations.
- Implemented failure classification and root-cause heuristics for infrastructure, configuration, dependency, flaky-test, resource and application failures.
- Added TF-IDF/K-Means clustering and stable failure signatures to identify related and recurring failures across test executions.
- Developed guarded self-healing plans for selected failure types, distinguishing safe controlled retries from configuration, dependency and resource changes requiring validation or approval.
- Exposed workflows through FastAPI and Streamlit with Docker/Kubernetes deployment, Pytest coverage and GitHub Actions CI.
