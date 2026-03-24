"""
Centralized configuration loader.
Reads config.yaml, then applies environment variable overrides.
"""

import os
from typing import Any, Dict
from pathlib import Path

import yaml
from dotenv import load_dotenv

# Load .env file if present (does NOT override existing env vars)
load_dotenv()


class Config:
    """Hierarchical configuration: config.yaml → environment variables."""

    def __init__(self, config_path: str = "config.yaml"):
        self.config_path = Path(config_path)
        self._config: Dict[str, Any] = {}
        self._load_config()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _load_config(self) -> None:
        if self.config_path.exists():
            with open(self.config_path, "r") as f:
                self._config = yaml.safe_load(f) or {}
        self._apply_env_overrides()

    def _apply_env_overrides(self) -> None:
        """Environment variables take precedence over config.yaml values."""
        env_map = {
            "OPENAI_API_KEY":   ("llm", "api_key"),
            "ANTHROPIC_API_KEY": ("llm", "api_key"),
            "LLM_PROVIDER":     ("llm", "provider"),
            "LLM_MODEL":        ("llm", "model"),
            "API_PORT":         ("api", "port"),
        }
        for env_var, path in env_map.items():
            value = os.environ.get(env_var)
            if value is not None:
                section, key = path
                self._config.setdefault(section, {})[key] = value

        # Coerce port to int
        try:
            self._config.setdefault("api", {})["port"] = int(
                self._config.get("api", {}).get("port", 8000)
            )
        except (ValueError, TypeError):
            self._config.setdefault("api", {})["port"] = 8000

    # ------------------------------------------------------------------
    # Generic accessor
    # ------------------------------------------------------------------
    def get(self, key: str, default: Any = None) -> Any:
        """Dot-notation accessor, e.g. config.get('llm.model')."""
        keys = key.split(".")
        value: Any = self._config
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return default
            if value is None:
                return default
        return value

    # ------------------------------------------------------------------
    # Typed convenience properties
    # ------------------------------------------------------------------
    @property
    def llm_provider(self) -> str:
        return self.get("llm.provider", "openai")

    @property
    def llm_model(self) -> str:
        return self.get("llm.model", "gpt-4")

    @property
    def llm_api_key(self) -> str:
        return self.get("llm.api_key", "")

    @property
    def llm_temperature(self) -> float:
        return float(self.get("llm.temperature", 0.7))

    @property
    def llm_max_tokens(self) -> int:
        return int(self.get("llm.max_tokens", 4096))

    @property
    def memory_type(self) -> str:
        return self.get("memory.type", "sqlite")

    @property
    def memory_db_path(self) -> str:
        return self.get("memory.db_path", "./memory/agent_memory.db")

    @property
    def output_dir(self) -> str:
        return self.get("file_generation.output_dir", "./generated_projects")

    @property
    def default_framework(self) -> str:
        return self.get("file_generation.default_framework", "nextjs")

    @property
    def default_styling(self) -> str:
        return self.get("file_generation.default_styling", "tailwindcss")

    @property
    def api_host(self) -> str:
        return self.get("api.host", "0.0.0.0")

    @property
    def api_port(self) -> int:
        return int(self.get("api.port", 8000))


# Singleton instance used throughout the app
config = Config()
