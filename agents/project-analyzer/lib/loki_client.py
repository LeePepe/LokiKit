"""Thin Loki HTTP client.

Uses the `query_range` endpoint. Returns normalized, immutable result tuples.
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Mapping, Tuple

import requests


class LokiError(RuntimeError):
    """Raised for network / HTTP / parse errors when talking to Loki."""


@dataclass(frozen=True)
class LogEntry:
    ts_ns: int           # nanosecond unix timestamp
    line: str            # raw log line
    labels: Mapping[str, str]


@dataclass(frozen=True)
class QueryResult:
    query: str
    entries: Tuple[LogEntry, ...]
    truncated: bool      # whether the server returned >= limit entries


def _parse_duration_ns(expr: str) -> int:
    """Parse 1h / 30m / 15s / 250ms into nanoseconds. Validates input."""
    if not isinstance(expr, str) or not expr:
        raise LokiError(f"Invalid duration: {expr!r}")
    units = {"ms": 1_000_000, "s": 1_000_000_000,
             "m": 60 * 1_000_000_000, "h": 3600 * 1_000_000_000,
             "d": 86400 * 1_000_000_000}
    # Longest-unit-first matching.
    for suffix in ("ms", "s", "m", "h", "d"):
        if expr.endswith(suffix):
            num = expr[: -len(suffix)]
            try:
                val = float(num)
            except ValueError as e:
                raise LokiError(f"Invalid duration number in {expr!r}: {e}") from e
            if val < 0:
                raise LokiError(f"Duration cannot be negative: {expr!r}")
            return int(val * units[suffix])
    raise LokiError(f"Unknown duration suffix in {expr!r}")


class LokiClient:
    """Immutable-by-convention client: state set at construction time."""

    def __init__(self, base_url: str, timeout: int = 30, token: str | None = None):
        if not base_url.startswith(("http://", "https://")):
            raise LokiError(f"Invalid base_url: {base_url!r}")
        if timeout <= 0:
            raise LokiError("timeout must be positive")
        self._base = base_url.rstrip("/")
        self._timeout = timeout
        self._session = requests.Session()
        headers = {"Accept": "application/json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        self._session.headers.update(headers)

    # ---- public API ----

    def query_range(
        self,
        logql: str,
        lookback: str,
        *,
        limit: int = 5000,
        end_ns: int | None = None,
    ) -> QueryResult:
        """Run a LogQL query over [now - lookback, now]."""
        if not logql or not isinstance(logql, str):
            raise LokiError("logql must be a non-empty string")
        if limit <= 0:
            raise LokiError("limit must be positive")
        end = end_ns if end_ns is not None else time.time_ns()
        start = end - _parse_duration_ns(lookback)
        params = {
            "query": logql,
            "start": str(start),
            "end": str(end),
            "limit": str(limit),
            "direction": "backward",
        }
        url = f"{self._base}/loki/api/v1/query_range"
        try:
            resp = self._session.get(url, params=params, timeout=self._timeout)
        except requests.RequestException as e:
            raise LokiError(f"Loki request failed: {e}") from e
        if resp.status_code != 200:
            raise LokiError(
                f"Loki returned HTTP {resp.status_code}: {resp.text[:200]}"
            )
        try:
            payload = resp.json()
        except json.JSONDecodeError as e:
            raise LokiError(f"Invalid JSON from Loki: {e}") from e
        return _parse_payload(logql, payload, limit)


def _parse_payload(query: str, payload: Mapping, limit: int) -> QueryResult:
    if not isinstance(payload, Mapping) or payload.get("status") != "success":
        raise LokiError(f"Unsuccessful response: {str(payload)[:200]}")
    data = payload.get("data") or {}
    result_type = data.get("resultType")
    if result_type not in ("streams", "matrix", "vector"):
        raise LokiError(f"Unexpected resultType: {result_type}")
    entries: list[LogEntry] = []
    for stream in data.get("result", []) or []:
        labels = stream.get("stream") or stream.get("metric") or {}
        if not isinstance(labels, Mapping):
            labels = {}
        frozen_labels = tuple(sorted(labels.items()))
        label_map = dict(frozen_labels)
        for value in stream.get("values", []) or []:
            if not (isinstance(value, (list, tuple)) and len(value) >= 2):
                continue
            try:
                ts_ns = int(value[0])
            except (TypeError, ValueError):
                continue
            line = str(value[1])
            entries.append(LogEntry(ts_ns=ts_ns, line=line, labels=label_map))
    truncated = len(entries) >= limit
    return QueryResult(query=query, entries=tuple(entries), truncated=truncated)
