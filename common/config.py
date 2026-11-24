"""Central configuration loader for the Financial Transaction Enrichment Engine.

All components import `CFG` from here. Values come from
``config/project_config.yaml`` and can be overridden with environment variables
of the form ``FEBAR_<SECTION>_<KEY>`` (upper-cased), e.g.
``FEBAR_MODELS_CHAT_ENDPOINT=databricks-gpt-5``.

This keeps catalog/schema/endpoint/resource names parameterized (per the spec:
"Parameterize catalog, schema, endpoints, and resource names").
"""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "project_config.yaml"


class _Section(dict):
    """Dict that also allows attribute access and env-var overrides."""

    def __init__(self, prefix: str, data: dict):
        super().__init__()
        for key, value in data.items():
            env_key = f"FEBAR_{prefix}_{key}".upper()
            if env_key in os.environ:
                value = _coerce(os.environ[env_key], value)
            self[key] = value

    def __getattr__(self, item: str) -> Any:
        try:
            return self[item]
        except KeyError as exc:  # pragma: no cover
            raise AttributeError(item) from exc


def _coerce(raw: str, template: Any) -> Any:
    """Coerce an env-var string to the type of the YAML default."""
    if isinstance(template, bool):
        return raw.lower() in ("1", "true", "yes", "on")
    if isinstance(template, int):
        return int(raw)
    if isinstance(template, float):
        return float(raw)
    return raw


class Config:
    def __init__(self, path: Path = _CONFIG_PATH):
        with open(path) as fh:
            raw = yaml.safe_load(fh)
        for section, data in raw.items():
            setattr(self, section, _Section(section, data))

    # ---- Convenience accessors used throughout the codebase --------------
    @property
    def catalog(self) -> str:
        return self.unity_catalog["catalog"]

    @property
    def schema(self) -> str:
        return self.unity_catalog["schema"]

    def table(self, name: str) -> str:
        """Fully-qualified UC table name."""
        return f"{self.catalog}.{self.schema}.{name}"

    @property
    def volume_path(self) -> str:
        return f"/Volumes/{self.catalog}/{self.schema}/{self.unity_catalog['volume']}"

    @property
    def profile(self) -> str:
        return os.environ.get("FEBAR_PROFILE", self.databricks["profile"])

    @property
    def host(self) -> str:
        return os.environ.get("DATABRICKS_HOST", self.databricks["host"])


@lru_cache(maxsize=1)
def get_config() -> Config:
    return Config()


CFG = get_config()
