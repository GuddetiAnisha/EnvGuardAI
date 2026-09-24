from copy import deepcopy

def repair_environment(payload: dict) -> tuple[dict, list[str]]:
    repaired = deepcopy(payload)
    actions: list[str] = []
    repaired.setdefault("environment_name", "integration-env")
    repaired.setdefault("environment_type", "integration")
    repaired.setdefault("namespace", "envguard-test")
    repaired.setdefault("services", [])
    repaired.setdefault("required_secrets", [])
    repaired.setdefault("metadata", {})

    for idx, svc in enumerate(repaired.get("services", [])):
        if not svc.get("name"):
            svc["name"] = f"service-{idx+1}"
            actions.append(f"Assigned name service-{idx+1}.")
        if not svc.get("image"):
            svc["image"] = "example/service:latest"
            actions.append(f"Added placeholder image for {svc['name']}.")
        elif ":" not in svc["image"]:
            svc["image"] += ":latest"
            actions.append(f"Added explicit image tag to {svc['name']}.")
        svc.setdefault("port", 8080 + idx)
        svc.setdefault("health_path", "/health")
        resources = svc.setdefault("resources", {})
        resources.setdefault("cpu", 0.5)
        resources.setdefault("memory_mb", 256)
        resources.setdefault("replicas", 1)
        svc.setdefault("required", True)

    if repaired.get("environment_type") in {"integration", "system", "performance"}:
        repaired.setdefault("database", {
            "engine": "postgres",
            "host": "postgres",
            "port": 5432,
            "persistent_storage_gb": 2,
            "required": True,
        })

    repaired["auto_repair"] = True
    return repaired, actions
