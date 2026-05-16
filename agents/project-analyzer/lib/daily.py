"""Daily summary aggregation module.

Produces per-project daily JSON summaries covering:
  (a) STORAGE - ingested bytes/streams/chunks via Loki index/stats
  (b) USAGE   - distinct actions, unique sessions, top actions over 24h
  (c) PERFORMANCE - p50/p95/p99 vs previous 24h baseline

Output: <project>/<YYYY-MM-DD>.daily.json (machine-readable).
"""
from __future__ import annotations

import json
import logging
from collections import Counter
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence, Tuple

from .analyzer import (
    ActionStats,
    PerfStats,
    ProjectReport,
    summarize_actions,
    summarize_performance,
    _action_name,
    _try_json,
)
from .loki_client import LogEntry, QueryResult
from .loki_stats import StorageStats, query_index_stats

log = logging.getLogger("daily-analyzer")


@dataclass(frozen=True)
class UsageStats:
    """Usage summary over 24h window."""
    total_actions: int
    distinct_action_count: int
    unique_sessions: int
    top_actions: Tuple[Tuple[str, int], ...]  # (action_name, count) top 10
    error_count: int
    error_rate: float


@dataclass(frozen=True)
class PerformanceComparison:
    """Performance stats with baseline comparison."""
    current_p50_ms: float
    current_p95_ms: float
    current_p99_ms: float
    baseline_p50_ms: float
    baseline_p95_ms: float
    baseline_p99_ms: float
    samples_current: int
    samples_baseline: int
    p95_change_pct: float  # positive = regression


@dataclass(frozen=True)
class DailySummary:
    """Complete daily summary for one project."""
    project: str
    date: str  # YYYY-MM-DD
    generated_at: str  # ISO8601
    storage: StorageStats
    usage: UsageStats
    performance: PerformanceComparison


def _extract_session_id(entry: LogEntry) -> str | None:
    """Extract session_id from log entry JSON or labels."""
    obj = _try_json(entry.line)
    if obj:
        for key in ("session_id", "sessionId", "session"):
            v = obj.get(key)
            if isinstance(v, str) and v:
                return v
    return entry.labels.get("session_id") or entry.labels.get("session")


def compute_usage_stats(result: QueryResult) -> UsageStats:
    """Compute usage summary from a query result of user_action entries."""
    action_counts: Counter[str] = Counter()
    sessions: set[str] = set()
    errors = 0

    for entry in result.entries:
        action = _action_name(entry) or "<unknown>"
        action_counts[action] += 1
        sess = _extract_session_id(entry)
        if sess:
            sessions.add(sess)
        # Reuse error detection from analyzer
        obj = _try_json(entry.line)
        if obj:
            level = str(obj.get("level", "")).lower()
            if level in ("error", "err", "fatal", "critical"):
                errors += 1

    total = len(result.entries)
    top = tuple(action_counts.most_common(10))
    return UsageStats(
        total_actions=total,
        distinct_action_count=len(action_counts),
        unique_sessions=len(sessions),
        top_actions=top,
        error_count=errors,
        error_rate=(errors / total) if total else 0.0,
    )


def compute_performance_comparison(
    current: PerfStats, baseline: PerfStats
) -> PerformanceComparison:
    """Compare current vs baseline performance stats."""
    change = 0.0
    if baseline.p95_ms and baseline.p95_ms > 0:
        change = ((current.p95_ms - baseline.p95_ms) / baseline.p95_ms) * 100.0
    return PerformanceComparison(
        current_p50_ms=current.p50_ms,
        current_p95_ms=current.p95_ms,
        current_p99_ms=current.p99_ms,
        baseline_p50_ms=baseline.p50_ms,
        baseline_p95_ms=baseline.p95_ms,
        baseline_p99_ms=baseline.p99_ms,
        samples_current=current.samples,
        samples_baseline=baseline.samples,
        p95_change_pct=round(change, 2),
    )


def build_daily_summary(
    *,
    project_name: str,
    date: str,
    storage: StorageStats,
    usage: UsageStats,
    perf_comparison: PerformanceComparison,
) -> DailySummary:
    """Build a complete daily summary."""
    return DailySummary(
        project=project_name,
        date=date,
        generated_at=datetime.now(timezone.utc).isoformat(),
        storage=storage,
        usage=usage,
        performance=perf_comparison,
    )


def daily_summary_to_json(summary: DailySummary) -> str:
    """Serialize a DailySummary to a JSON string."""
    def _to_dict(obj: Any) -> Any:
        if hasattr(obj, "__dataclass_fields__"):
            return {k: _to_dict(v) for k, v in asdict(obj).items()}
        if isinstance(obj, tuple):
            return [_to_dict(i) for i in obj]
        return obj

    return json.dumps(_to_dict(summary), indent=2)


def write_daily_json(
    summary: DailySummary,
    output_dir: Path,
) -> Path:
    """Write daily JSON summary to reports/<project>/<date>.daily.json."""
    project_dir = output_dir / summary.project
    project_dir.mkdir(parents=True, exist_ok=True)
    path = project_dir / f"{summary.date}.daily.json"
    path.write_text(daily_summary_to_json(summary), encoding="utf-8")
    return path
