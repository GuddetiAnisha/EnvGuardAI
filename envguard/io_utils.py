from pathlib import Path
import json
import yaml

def load_config(path: str | Path) -> dict:
    path = Path(path)
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() in {".yaml", ".yml"}:
        return yaml.safe_load(text)
    if path.suffix.lower() == ".json":
        return json.loads(text)
    raise ValueError("Only YAML and JSON environment definitions are supported.")

def dump_yaml(data: dict) -> str:
    return yaml.safe_dump(data, sort_keys=False)
