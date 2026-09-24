# EnvGuardAI

AI-assisted data-quality validation and readiness orchestration for integration test environments.

This portfolio project is designed around the types of problems described in Ericsson's **Master Thesis: AI-Powered Autonomous Test Environment Orchestration (Job ID 789574)**. It does not contain Ericsson code or data.

## Core capabilities

- validates YAML/JSON environment definitions using typed schemas
- calculates a data-quality score and structured issues
- detects missing/invalid fields and cross-field quality problems
- performs deterministic AI-style repair suggestions without exposing data to an external LLM
- checks environment readiness before test execution
- supports optional live HTTP/TCP readiness checks
- exposes FastAPI endpoints for validation, repair and orchestration
- includes a Streamlit dashboard
- includes Docker, Kubernetes manifests and GitHub Actions CI
- includes Pytest automated tests

## Architecture

```text
Requirements / environment definition
                |
                v
      +--------------------+
      | Schema + DQ engine |
      +----------+---------+
                 |
        valid?---+---invalid
          |             |
          |             v
          |      +-------------+
          |      | Repair agent |
          |      +------+------+
          |             |
          +-------------+
                 |
                 v
       +------------------+
       | Readiness checks |
       | services / DB /  |
       | secrets / health |
       +--------+---------+
                |
                v
      READY / NOT READY
                |
                v
        Structured report
```

## Quick start

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

pip install -r requirements.txt
pytest -q

uvicorn api:app --reload
```

API docs: http://127.0.0.1:8000/docs

Dashboard:

```bash
streamlit run app.py
```

## Docker

```bash
docker compose up --build
```

## Kubernetes

Update the image in `k8s/deployment.yaml`, then:

```bash
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml
kubectl get pods
kubectl get svc
```

## CI/CD

`.github/workflows/ci.yml` runs automated tests on pushes and pull requests.

## CV-safe project description

**EnvGuardAI — AI-Powered Test Environment Orchestration**  
Python, FastAPI, Pydantic, Streamlit, Docker, Kubernetes, Pytest

- Built a configuration-quality and readiness orchestration prototype for integration test environments.
- Implemented typed schema validation, cross-field quality checks, quality scoring and structured repair suggestions for YAML/JSON environment definitions.
- Developed automated readiness checks for service definitions, container images, database dependencies, secrets and optional live HTTP/TCP health checks.
- Exposed validation, repair and orchestration through FastAPI, with Streamlit visualization, Docker/Kubernetes deployment and GitHub Actions CI.
