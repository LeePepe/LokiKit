"""Loki storage statistics queries.

Queries Loki's /loki/api/v1/index/stats endpoint for per-project storage info,
with fallback to counting log lines over 24h as a proxy.

All functions are best-effort and return empty/zero stats on failure.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Mapping

import requests

log = logging.getLogger("loki-stats")


@dataclass(frozen=True)
class StorageStats:
    """Per-project storage summary over a time window."""
    streams: int
    chunks: int
    bytes_total: int
    entries: int
    # Fallback: log line count (if index/stats unavailable)
    line_count_proxy: int


def _parse_duration_seconds(expr: str) -> int:
    """Parse '24h' / '48h' / '1d' into seconds."""
    units = {"s": 1, "m": 60, "h": 3600, "d": 86400}
    for suffix in ("ms", "s", "m", "h", "d"):
        if expr.endswith(suffix):
            num = expr[: -len(suffix)]
            return int(float(num) * units.get(suffix, 1))
    return 86400  # default 24h


def query_index_stats(
    base_url: str,
    app_label: str,
    lookback: str = "24h",
    timeout: int = 15,
    token: str | None = None,
) -> StorageStats:
    """Query Loki /loki/api/v1/index/stats for a given app label.

    Returns StorageStats with best-effort fields. On failure, returns zeroed stats.
    """
    url = f"{base_url.rstrip('/')}/loki/api/v1/index/stats"
    end_ns = time.time_ns()
    secs = _parse_duration_seconds(lookback)
    start_ns = end_ns - secs * 1_000_000_000

    headers: dict[str, str] = {"Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    params = {
        "query": f'{{app="{app_label}"}}',
        "start": str(start_ns),
        "end": str(end_ns),
    }

    try:
        resp = requests.get(url, params=params, headers=headers, timeout=timeout)
        if resp.status_code == 200:
            data = resp.json()
            return StorageStats(
                streams=int(data.get("streams", 0)),
                chunks=int(data.get("chunks", 0)),
                bytes_total=int(data.get("bytes", 0)),
                entries=int(data.get("entries", 0)),
                line_count_proxy=int(data.get("entries", 0)),
            )
        log.warning("index/stats returned HTTP %d for app=%s", resp.status_code, app_label)
    except Exception as exc:
        log.warning("index/stats query failed for app=%s: %s", app_label, exc)

    # Fallback: count lines via query_range count_over_time
    return _fallback_line_count(base_url, app_label, lookback, timeout, token)


def _fallback_line_count(
    base_url: str,
    app_label: str,
    lookback: str,
    timeout: int,
    token: str | None,
) -> StorageStats:
    """Fallback: use count_over_time as proxy for storage volume."""
    url = f"{base_url.rstrip('/')}/loki/api/v1/query"
    headers: dict[str, str] = {"Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    params = {
        "query": f'sum(count_over_time({{app="{app_label}"}} [{lookback}]))',
    }
    try:
        resp = requests.get(url, params=params, headers=headers, timeout=timeout)
        if resp.status_code == 200:
            data = resp.json()
            results = (data.get("data") or {}).get("result", [])
            count = 0
            for r in results:
                val = r.get("value", [None, "0"])
                if isinstance(val, (list, tuple)) and len(val) >= 2:
                    count += int(float(val[1]))
            return StorageStats(
                streams=0, chunks=0, bytes_total=0, entries=count,
                line_count_proxy=count,
            )
    except Exception as exc:
        log.debug("Fallback line count failed for app=%s: %s", app_label, exc)

    return StorageStats(streams=0, chunks=0, bytes_total=0, entries=0, line_count_proxy=0)


def parse_index_stats_response(data: Mapping) -> StorageStats:
    """Parse a raw Loki /index/stats JSON response into StorageStats.

    Exported for testing with mock responses.
    """
    return StorageStats(
        streams=int(data.get("streams", 0)),
        chunks=int(data.get("chunks", 0)),
        bytes_total=int(data.get("bytes", 0)),
        entries=int(data.get("entries", 0)),
        line_count_proxy=int(data.get("entries", 0)),
    )
