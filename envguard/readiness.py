import socket
import requests
from .models import EnvironmentSpec, ReadinessCheck, ReadinessResult

def _tcp_check(host: str, port: int, timeout: float = 1.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False

def evaluate_readiness(env: EnvironmentSpec, live_checks: bool = False) -> ReadinessResult:
    checks: list[ReadinessCheck] = []
    for svc in env.services:
        checks.append(ReadinessCheck(
            component=svc.name,
            check="resource_definition",
            status="pass",
            details=f"{svc.resources.cpu} CPU, {svc.resources.memory_mb} MB, replicas={svc.resources.replicas}",
        ))
        checks.append(ReadinessCheck(
            component=svc.name,
            check="image_tag",
            status="pass" if ":" in svc.image else "warning",
            details=svc.image,
        ))
        if live_checks:
            url = f"http://{svc.name}:{svc.port}{svc.health_path}"
            try:
                response = requests.get(url, timeout=1.5)
                status = "pass" if response.status_code < 400 else "fail"
                detail = f"{url} -> HTTP {response.status_code}"
            except requests.RequestException as exc:
                status = "fail" if svc.required else "warning"
                detail = f"{url} unavailable: {exc.__class__.__name__}"
            checks.append(ReadinessCheck(
                component=svc.name, check="http_health", status=status, details=detail
            ))

    if env.database:
        if live_checks:
            ok = _tcp_check(env.database.host, env.database.port)
            status = "pass" if ok else ("fail" if env.database.required else "warning")
            details = f"{env.database.host}:{env.database.port} {'reachable' if ok else 'unreachable'}"
        else:
            status = "pass"
            details = f"{env.database.engine} declared with {env.database.persistent_storage_gb} GiB storage"
        checks.append(ReadinessCheck(
            component="database", check="database_readiness", status=status, details=details
        ))

    for secret in env.required_secrets:
        checks.append(ReadinessCheck(
            component="secrets",
            check=f"declared:{secret}",
            status="pass",
            details="Secret dependency is explicitly declared.",
        ))

    weights = {"pass": 1.0, "warning": 0.5, "fail": 0.0}
    score = 100.0 * sum(weights[c.status] for c in checks) / max(len(checks), 1)
    ready = not any(c.status == "fail" for c in checks)
    return ReadinessResult(ready=ready, score=round(score, 2), checks=checks)
