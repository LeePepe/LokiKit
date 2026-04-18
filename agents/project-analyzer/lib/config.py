"""Configuration loading and validation for project-analyzer.

All returned objects are immutable (frozen dataclasses / tuples).
"""
from __future__ import annotations

import os
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Mapping, Sequence, Tuple

import yaml


class ConfigError(ValueError):
    """Raised when config is missing, malformed, or fails validation."""


@dataclass(frozen=True)
class LokiConfig:
    url: str
    lookback: str
    baseline_lookback: str
    timeout: int
    query_limit: int
    token: str | None = None


@dataclass(frozen=True)
class Thresholds:
    error_rate_spike: float
    error_count_min: int
    perf_regression_ratio: float
    silent_failure_ratio: float
    silent_failure_min_baseline: int


@dataclass(frozen=True)
class ProjectConfig:
    name: str
    repo_path: str
    team_lead: str
    selector_user_action: str
    selector_performance: str


@dataclass(frozen=True)
class AppConfig:
    loki: LokiConfig
    thresholds: Thresholds
    projects: Tuple[ProjectConfig, ...]


def _require(d: Mapping, key: str, ctx: str):
    if key not in d:
        raise ConfigError(f"Missing required key '{key}' in {ctx}")
    return d[key]


def _parse_project(raw: Mapping) -> ProjectConfig:
    name = str(_require(raw, "name", "project")).strip()
    if not name:
        raise ConfigError("Project name must be non-empty")
    repo_path = str(_require(raw, "repo_path", f"project[{name}]")).strip()
    team_lead = str(raw.get("team_lead", f"{name} team")).strip()
    selectors = _require(raw, "selectors", f"project[{name}]")
    if not isinstance(selectors, Mapping):
        raise ConfigError(f"project[{name}].selectors must be a mapping")
    ua = str(_require(selectors, "user_action", f"project[{name}].selectors")).strip()
    perf = str(_require(selectors, "performance", f"project[{name}].selectors")).strip()
    if not ua or not perf:
        raise ConfigError(f"project[{name}] selectors must be non-empty LogQL strings")
    return ProjectConfig(
        name=name,
        repo_path=repo_path,
        team_lead=team_lead,
        selector_user_action=ua,
        selector_performance=perf,
    )


def _parse_loki(raw: Mapping) -> LokiConfig:
    url = str(raw.get("url", "http://localhost:3100")).rstrip("/")
    if not url.startswith(("http://", "https://")):
        raise ConfigError(f"loki.url must be http(s) URL, got: {url!r}")
    try:
        timeout = int(raw.get("timeout", 30))
        query_limit = int(raw.get("query_limit", 5000))
    except (TypeError, ValueError) as e:
        raise ConfigError(f"loki timeout/query_limit must be integers: {e}") from e
    if timeout <= 0 or query_limit <= 0:
        raise ConfigError("loki timeout and query_limit must be positive")
    return LokiConfig(
        url=url,
        lookback=str(raw.get("lookback", "1h")),
        baseline_lookback=str(raw.get("baseline_lookback", "24h")),
        timeout=timeout,
        query_limit=query_limit,
        token=None,
    )


def _parse_thresholds(raw: Mapping) -> Thresholds:
    try:
        return Thresholds(
            error_rate_spike=float(raw.get("error_rate_spike", 0.05)),
            error_count_min=int(raw.get("error_count_min", 5)),
            perf_regression_ratio=float(raw.get("perf_regression_ratio", 1.5)),
            silent_failure_ratio=float(raw.get("silent_failure_ratio", 0.25)),
            silent_failure_min_baseline=int(raw.get("silent_failure_min_baseline", 20)),
        )
    except (TypeError, ValueError) as e:
        raise ConfigError(f"Invalid thresholds: {e}") from e


def load_config(path: str | Path) -> AppConfig:
    """Load config from YAML path. Applies LOKI_URL / LOKI_TOKEN env overrides."""
    p = Path(path).expanduser()
    if not p.is_file():
        raise ConfigError(f"Config file not found: {p}")
    try:
        with p.open("r", encoding="utf-8") as fh:
            raw = yaml.safe_load(fh) or {}
    except yaml.YAMLError as e:
        raise ConfigError(f"Failed to parse YAML {p}: {e}") from e
    if not isinstance(raw, Mapping):
        raise ConfigError(f"Config root must be a mapping in {p}")

    loki = _parse_loki(raw.get("loki") or {})
    thresholds = _parse_thresholds(raw.get("thresholds") or {})
    projects_raw = raw.get("projects") or []
    if not isinstance(projects_raw, Sequence) or not projects_raw:
        raise ConfigError("config.projects must be a non-empty list")
    projects = tuple(_parse_project(p) for p in projects_raw)

    env_url = os.environ.get("LOKI_URL")
    env_token = os.environ.get("LOKI_TOKEN")
    if env_url:
        loki = replace(loki, url=env_url.rstrip("/"))
    if env_token:
        loki = replace(loki, token=env_token)

    return AppConfig(loki=loki, thresholds=thresholds, projects=projects)


def filter_projects(cfg: AppConfig, name: str | None) -> Tuple[ProjectConfig, ...]:
    """Return immutable tuple filtered by name (case-insensitive), or all."""
    if name is None:
        return cfg.projects
    target = name.strip().lower()
    matched = tuple(p for p in cfg.projects if p.name.lower() == target)
    if not matched:
        known = ", ".join(p.name for p in cfg.projects)
        raise ConfigError(f"Unknown project '{name}'. Known: {known}")
    return matched
