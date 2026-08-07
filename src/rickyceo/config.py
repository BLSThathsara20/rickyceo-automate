from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = ROOT / "config.yaml"


def load_config(path: Path | None = None) -> dict[str, Any]:
    cfg_path = path or Path(os.environ.get("RICKYCEO_CONFIG", DEFAULT_CONFIG))
    with open(cfg_path, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    # Env overrides
    ollama = data.setdefault("ollama", {})
    if host := os.environ.get("OLLAMA_HOST"):
        ollama["host"] = host
    if model := os.environ.get("OLLAMA_MODEL"):
        ollama["model"] = model
    return data


def project_root() -> Path:
    return ROOT


def ensure_dirs() -> None:
    (ROOT / "output").mkdir(parents=True, exist_ok=True)
    (ROOT / "credentials").mkdir(parents=True, exist_ok=True)
    (ROOT / "assets" / "voices").mkdir(parents=True, exist_ok=True)
