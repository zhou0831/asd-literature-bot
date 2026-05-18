from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[1]


def load_dotenv(path: Path | None = None) -> None:
    env_path = path or ROOT / ".env"
    if not env_path.exists():
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def load_config(path: Path | None = None) -> dict[str, Any]:
    load_dotenv()
    config_path = path or ROOT / "config.yaml"
    with config_path.open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


def env(name: str, default: str = "") -> str:
    return os.environ.get(name) or default


def env_int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, str(default)))
    except ValueError:
        return default


def path_from_config(config: dict[str, Any], key: str) -> Path:
    raw = config.get("paths", {}).get(key, key)
    return ROOT / raw
