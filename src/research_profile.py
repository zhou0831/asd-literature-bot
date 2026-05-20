from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[1]
PROFILE_PATH = ROOT / "config" / "research_profile.yaml"


def load_research_profile(path: Path | None = None) -> dict[str, Any]:
    profile_path = path or PROFILE_PATH
    if not profile_path.exists():
        return {}
    with profile_path.open("r", encoding="utf-8-sig") as fh:
        return yaml.safe_load(fh) or {}

