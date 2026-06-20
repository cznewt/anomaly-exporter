"""Configuration loading and validation.

The config mirrors blackbox_exporter's ``modules:`` layout: every module names a
``detector`` and carries that detector's parameters in a block keyed by the
detector name (just as blackbox keys a prober's options under ``http:`` / ``tcp:``).
Common knobs (lookback, step, eval_points, labels, ...) live at module level.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

_DURATION_RE = re.compile(r"^\s*(\d+(?:\.\d+)?)\s*(ms|s|m|h|d|w)?\s*$")
_UNIT_SECONDS = {"ms": 1e-3, "s": 1.0, "m": 60.0, "h": 3600.0, "d": 86400.0, "w": 604800.0}


class ConfigError(Exception):
    """Raised when the configuration file is malformed."""


def parse_duration(value: Any, *, default_unit: str = "s") -> float:
    """Parse ``'5m'`` / ``'7d'`` / ``'30s'`` / ``'500ms'`` / ``90`` into seconds."""
    if value is None:
        raise ConfigError("missing duration value")
    if isinstance(value, bool):  # bool is an int subclass; reject it explicitly
        raise ConfigError(f"invalid duration: {value!r}")
    if isinstance(value, (int, float)):
        return float(value)
    m = _DURATION_RE.match(str(value))
    if not m:
        raise ConfigError(f"invalid duration: {value!r}")
    num, unit = m.group(1), m.group(2) or default_unit
    return float(num) * _UNIT_SECONDS[unit]


@dataclass
class PromConfig:
    """The backing Prometheus the exporter queries (the data source)."""

    url: str
    tenant: str = ""
    token: str = ""
    timeout: float = 60.0


@dataclass
class Module:
    """One named probe configuration: a detector plus its parameters."""

    name: str
    detector: str
    lookback: float            # seconds of history to fetch
    step: str                  # query resolution, passed straight to Prometheus
    eval_points: int = 12      # trailing points held out and scored
    min_train_points: int = 30
    labels: list[str] = field(default_factory=list)
    timeout: float | None = None   # optional per-module cap (seconds)
    query: str | None = None       # optional template containing {{target}}
    params: dict[str, Any] = field(default_factory=dict)  # detector-specific block

    def resolve_query(self, target: str) -> str:
        """The PromQL to run: a ``{{target}}`` template, or the raw target."""
        if self.query:
            return self.query.replace("{{target}}", target)
        return target


@dataclass
class Config:
    prometheus: PromConfig
    modules: dict[str, Module]
    path: str | None = None


def load_config(path: str | Path) -> Config:
    raw = yaml.safe_load(Path(path).read_text()) or {}
    return parse_config(raw, path=str(path))


def parse_config(raw: Any, path: str | None = None) -> Config:
    # Imported here (not at module top) so config parsing has no heavy deps.
    from .detectors import DETECTORS

    if not isinstance(raw, dict):
        raise ConfigError("top-level config must be a mapping")

    prom_raw = raw.get("prometheus") or {}
    if not isinstance(prom_raw, dict) or "url" not in prom_raw:
        raise ConfigError("prometheus.url is required")
    token = str(prom_raw.get("token", "") or "")
    token_file = prom_raw.get("token_file")
    if token_file:
        token = Path(token_file).read_text().strip()
    prom = PromConfig(
        url=str(prom_raw["url"]).rstrip("/"),
        tenant=str(prom_raw.get("tenant", "") or ""),
        token=token,
        timeout=parse_duration(prom_raw.get("timeout", 60)),
    )

    modules_raw = raw.get("modules") or {}
    if not isinstance(modules_raw, dict) or not modules_raw:
        raise ConfigError("at least one module is required under 'modules'")
    modules = {
        name: _parse_module(name, mraw, DETECTORS)
        for name, mraw in modules_raw.items()
    }
    return Config(prometheus=prom, modules=modules, path=path)


def _parse_module(name: str, mraw: Any, detectors: dict) -> Module:
    if not isinstance(mraw, dict):
        raise ConfigError(f"module {name!r} must be a mapping")
    detector = mraw.get("detector")
    if not detector:
        raise ConfigError(f"module {name!r}: 'detector' is required")
    if detector not in detectors:
        raise ConfigError(
            f"module {name!r}: unknown detector {detector!r} "
            f"(known: {', '.join(sorted(detectors))})"
        )
    for required in ("lookback", "step"):
        if required not in mraw:
            raise ConfigError(f"module {name!r}: '{required}' is required")
    params = mraw.get(detector) or {}
    if not isinstance(params, dict):
        raise ConfigError(f"module {name!r}: '{detector}' block must be a mapping")
    timeout = mraw.get("timeout")
    return Module(
        name=name,
        detector=detector,
        lookback=parse_duration(mraw["lookback"]),
        step=str(mraw["step"]),
        eval_points=int(mraw.get("eval_points", 12)),
        min_train_points=int(mraw.get("min_train_points", 30)),
        labels=list(mraw.get("labels", []) or []),
        timeout=parse_duration(timeout) if timeout is not None else None,
        query=mraw.get("query"),
        params=params,
    )


def redacted(config: Config) -> dict:
    """Config as a JSON-serialisable dict with the bearer token masked."""
    return {
        "prometheus": {
            "url": config.prometheus.url,
            "tenant": config.prometheus.tenant,
            "token": "<redacted>" if config.prometheus.token else "",
            "timeout": config.prometheus.timeout,
        },
        "modules": {
            name: {
                "detector": m.detector,
                "lookback": m.lookback,
                "step": m.step,
                "eval_points": m.eval_points,
                "min_train_points": m.min_train_points,
                "labels": m.labels,
                "timeout": m.timeout,
                "query": m.query,
                m.detector: m.params,
            }
            for name, m in config.modules.items()
        },
    }
