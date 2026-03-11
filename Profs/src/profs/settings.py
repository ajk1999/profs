from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from profs.utils import load_yaml_file, merge_nested_dicts


@dataclass
class Settings:
    openai_api_key: str = ""
    openai_model: str = "gpt-4.1-mini"
    output_dir: str = "outputs"
    request_delay: float = 1.0
    timeout: int = 20
    max_retries: int = 3
    alignment_context: str = ""
    openalex_mailto: str = ""
    user_agent: str = (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
    )


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def load_env_file(env_path: str | Path = ".env") -> None:
    path = Path(env_path)
    if not path.exists():
        return

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


def load_settings(env_path: str | Path = ".env") -> Settings:
    load_env_file(env_path)
    return Settings(
        openai_api_key=os.getenv("OPENAI_API_KEY", ""),
        openai_model=os.getenv("PROFS_OPENAI_MODEL", "gpt-4.1-mini"),
        output_dir=os.getenv("PROFS_OUTPUT_DIR", "outputs"),
        request_delay=float(os.getenv("PROFS_REQUEST_DELAY", "1.0")),
        timeout=int(os.getenv("PROFS_TIMEOUT", "20")),
        max_retries=int(os.getenv("PROFS_MAX_RETRIES", "3")),
        alignment_context=os.getenv("PROFS_ALIGNMENT_CONTEXT", ""),
        openalex_mailto=os.getenv("OPENALEX_MAILTO", ""),
    )


def load_university_config(config_path: str | None = None) -> dict:
    default_path = project_root() / "config" / "universities" / "default.yaml"
    config = load_yaml_file(default_path)

    if config_path:
        specific = load_yaml_file(config_path)
        config = merge_nested_dicts(config, specific)

    return config
