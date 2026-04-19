"""Anomaly / regression / error-spike / silent-failure detection.

Pure functions over immutable inputs. No I/O here.
"""
from __future__ import annotations

import json
import statistics
from dataclasses import dataclass
from typing import Sequence, Tuple

from .config import Thresholds
from .loki_client import LogEntry, QueryResult


# ---- domain models ----

@dataclass(frozen=True)
class ActionStats:
    total: int
    errors: int
    error_rate: float
    top_errors: Tuple[Tuple[str, int], ...]  # (error_key, count) descending


@dataclass(frozen=True)
class PerfStats:
    samples: int
    p50_ms: float
    p95_ms: float
    p99_ms: float
    slowest_ops: Tuple[Tuple[str, float], ...]  # (op_name, p95_ms)


@dataclass(frozen=True)
class Finding:
    severity: str           # "low" | "medium" | "high" | "critical"
    kind: str               # "error_spike" | "regression" | "silent_failure" | "anomaly"
    title: str
    detail: str
    suggested_fix: str


@dataclass(frozen=True)
class ProjectReport:
    project: str
    repo_path: str
    team_lead: str
    action_stats: ActionStats
    perf_stats: PerfStats
    baseline_actions: int
    baseline_p95_ms: float | None
    findings: Tuple[Finding, ...]


# ---- parsers ----

_ERROR_LEVELS = frozenset({"error", "err", "fatal", "critical"})


def _try_json(line: str) -> dict | None:
    line = line.strip()
    if not line or not line.startswith("{"):
        return None
    try:
        obj = json.loads(line)
    except (json.JSONDecodeError, ValueError):
        return None
    return obj if isinstance(obj, dict) else None


def _is_error_entry(entry: LogEntry) -> bool:
    # Check labels first (level, severity).
    for lbl in ("level", "severity", "status"):
        val = entry.labels.get(lbl)
        if val and str(val).lower() in _ERROR_LEVELS:
            return True
    obj = _try_json(entry.line)
    if obj:
        for key in ("level", "severity", "status"):
            val = obj.get(key)
            if val and str(val).lower() in _ERROR_LEVELS:
                return True
        if obj.get("error") or obj.get("err") or obj.get("exception"):
            return True
    lowered = entry.line.lower()
    return any(marker in lowered for marker in (" error ", "\"error\"", "exception", "traceback", "fatal"))


def _error_key(entry: LogEntry) -> str:
    obj = _try_json(entry.line)
    if obj:
        for key in ("error_type", "error_code", "code", "action", "name", "message"):
            v = obj.get(key)
            if isinstance(v, (str, int)) and str(v).strip():
                return str(v)[:120]
    # Fall back to first 80 chars of line.
    return entry.line.strip()[:80] or "<empty>"


def _action_name(entry: LogEntry) -> str | None:
    obj = _try_json(entry.line)
    if obj:
        for key in ("action", "event", "name"):
            v = obj.get(key)
            if isinstance(v, str) and v:
                return v
    return entry.labels.get("action")


def _duration_ms(entry: LogEntry) -> float | None:
    obj = _try_json(entry.line)
    if not obj:
        return None
    for key in ("duration_ms", "latency_ms", "elapsed_ms", "took_ms"):
        v = obj.get(key)
        if isinstance(v, (int, float)) and v >= 0:
            return float(v)
    # Some formats use seconds.
    for key in ("duration", "latency", "elapsed"):
        v = obj.get(key)
        if isinstance(v, (int, float)) and v >= 0:
            # Heuristic: > 10 → already ms; otherwise seconds.
            return float(v) if v > 10 else float(v) * 1000.0
    return None


# ---- aggregators ----

def summarize_actions(result: QueryResult) -> ActionStats:
    total = len(result.entries)
    errors = 0
    err_counts: dict[str, int] = {}
    for e in result.entries:
        if _is_error_entry(e):
            errors += 1
            key = _error_key(e)
            err_counts[key] = err_counts.get(key, 0) + 1
    top = tuple(sorted(err_counts.items(), key=lambda kv: kv[1], reverse=True)[:5])
    rate = (errors / total) if total else 0.0
    return ActionStats(total=total, errors=errors, error_rate=rate, top_errors=top)


def summarize_performance(result: QueryResult) -> PerfStats:
    durations: list[float] = []
    by_op: dict[str, list[float]] = {}
    for e in result.entries:
        d = _duration_ms(e)
        if d is None:
            continue
        durations.append(d)
        name = _action_name(e) or "<unknown>"
        by_op.setdefault(name, []).append(d)
    if not durations:
        return PerfStats(samples=0, p50_ms=0.0, p95_ms=0.0, p99_ms=0.0, slowest_ops=())
    p50 = _percentile(durations, 50)
    p95 = _percentile(durations, 95)
    p99 = _percentile(durations, 99)
    slowest = tuple(
        sorted(
            ((op, _percentile(vals, 95)) for op, vals in by_op.items() if vals),
            key=lambda kv: kv[1],
            reverse=True,
        )[:5]
    )
    return PerfStats(
        samples=len(durations), p50_ms=p50, p95_ms=p95, p99_ms=p99, slowest_ops=slowest
    )


def _percentile(values: Sequence[float], pct: float) -> float:
    if not values:
        return 0.0
    sorted_vals = sorted(values)
    if len(sorted_vals) == 1:
        return float(sorted_vals[0])
    # Nearest-rank, clipped to [0, len-1].
    k = max(0, min(len(sorted_vals) - 1, int(round((pct / 100.0) * (len(sorted_vals) - 1)))))
    return float(sorted_vals[k])


# ---- detectors ----

def detect_findings(
    *,
    project: str,
    repo_path: str,
    actions: ActionStats,
    perf: PerfStats,
    baseline_actions: int,
    baseline_p95_ms: float | None,
    thresholds: Thresholds,
) -> Tuple[Finding, ...]:
    findings: list[Finding] = []

    # Error spike.
    if (
        actions.errors >= thresholds.error_count_min
        and actions.error_rate >= thresholds.error_rate_spike
    ):
        top_desc = ", ".join(f"{k} ({c})" for k, c in actions.top_errors[:3]) or "n/a"
        findings.append(Finding(
            severity="high" if actions.error_rate >= 2 * thresholds.error_rate_spike else "medium",
            kind="error_spike",
            title=f"Error rate {actions.error_rate:.1%} exceeds threshold",
            detail=(
                f"{actions.errors}/{actions.total} user actions errored in the lookback window. "
                f"Top errors: {top_desc}."
            ),
            suggested_fix=(
                f"Inspect `{repo_path}` for regressions in the noisiest actions above. "
                f"Add targeted assertions / retries, and ensure these errors surface in "
                f"`{project}`'s main dashboard."
            ),
        ))

    # Silent failure.
    if (
        baseline_actions >= thresholds.silent_failure_min_baseline
        and actions.total <= int(baseline_actions * thresholds.silent_failure_ratio)
    ):
        findings.append(Finding(
            severity="high",
            kind="silent_failure",
            title="User action volume dropped sharply vs baseline",
            detail=(
                f"Observed {actions.total} actions in recent window vs "
                f"~{baseline_actions} in baseline window. "
                f"This may indicate a silent client-side failure to emit logs."
            ),
            suggested_fix=(
                f"Verify the telemetry client in `{repo_path}` is initialized and flushing: "
                f"check LOKI_ENDPOINT wiring, network/DNS, and startup ordering. "
                f"Consider adding a startup heartbeat log."
            ),
        ))

    # Performance regression.
    if (
        baseline_p95_ms is not None
        and baseline_p95_ms > 0
        and perf.samples > 0
        and perf.p95_ms >= baseline_p95_ms * thresholds.perf_regression_ratio
    ):
        slowest_desc = ", ".join(f"{op} ({v:.0f}ms)" for op, v in perf.slowest_ops[:3]) or "n/a"
        findings.append(Finding(
            severity="medium",
            kind="regression",
            title=f"p95 latency {perf.p95_ms:.0f}ms regressed vs baseline {baseline_p95_ms:.0f}ms",
            detail=(
                f"Slowest ops: {slowest_desc}. Ratio "
                f"{perf.p95_ms / baseline_p95_ms:.2f}× threshold "
                f"{thresholds.perf_regression_ratio:.2f}×."
            ),
            suggested_fix=(
                f"Profile the slowest ops in `{repo_path}` (see 'Slowest ops' above). "
                f"Look for recent changes in hot paths; add timing around suspected calls."
            ),
        ))

    # Generic anomaly: mean vs stdev of error counts per-minute (very lightweight).
    # (Kept optional — requires dense data; skipped when empty.)
    if actions.total == 0 and baseline_actions == 0:
        findings.append(Finding(
            severity="low",
            kind="anomaly",
            title="No telemetry observed (recent and baseline)",
            detail="No user_action entries in either window; the integration may not be wired up.",
            suggested_fix=(
                f"Confirm `{project}` is initialized against this Loki stack and emits "
                f"`stream=user_action` labels."
            ),
        ))

    return tuple(findings)


def build_report(
    *,
    project: str,
    repo_path: str,
    team_lead: str,
    actions: ActionStats,
    perf: PerfStats,
    baseline_actions: int,
    baseline_p95_ms: float | None,
    thresholds: Thresholds,
) -> ProjectReport:
    findings = detect_findings(
        project=project,
        repo_path=repo_path,
        actions=actions,
        perf=perf,
        baseline_actions=baseline_actions,
        baseline_p95_ms=baseline_p95_ms,
        thresholds=thresholds,
    )
    return ProjectReport(
        project=project,
        repo_path=repo_path,
        team_lead=team_lead,
        action_stats=actions,
        perf_stats=perf,
        baseline_actions=baseline_actions,
        baseline_p95_ms=baseline_p95_ms,
        findings=findings,
    )


# Expose a helper for tests / callers that have stdev needs.
def stdev_or_zero(values: Sequence[float]) -> float:
    if len(values) < 2:
        return 0.0
    try:
        return float(statistics.stdev(values))
    except statistics.StatisticsError:
        return 0.0
