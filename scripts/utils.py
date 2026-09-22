"""Shared helpers: config loading, paths, JSON read/write."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def project_path(*parts: str) -> Path:
    return PROJECT_ROOT.joinpath(*parts)


def load_config() -> dict[str, Any]:
    config_file = project_path("config", "settings.yaml")
    with config_file.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def today_str() -> str:
    return date.today().isoformat()
