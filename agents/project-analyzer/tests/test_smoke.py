"""Smoke tests: config loading + report formatting with a mocked Loki response.

Runnable both via pytest and directly:
    python3 -m pytest agents/project-analyzer/tests/ -q
    python3 agents/project-analyzer/tests/test_smoke.py
"""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lib.analyzer import summarize_actions, summarize_performance  # noqa: E402
from lib.config import load_config  # noqa: E402
from lib.loki_client import LokiClient, LogEntry, QueryResult  # noqa: E402
from lib.report import format_remediation_brief, format_report  # noqa: E402
from run import _analyze_project, build_arg_parser, write_report_files  # noqa: E402


CONFIG_PATH = ROOT / "config.yaml"


def _fake_loki_payload(lines):
    values = [[str(ts), line] for ts, line in lines]
    return {
        "status": "success",
        "data": {
            "resultType": "streams",
            "result": [
                {
                    "stream": {"app": "Financial", "level": "info"},
                    "values": values,
                }
            ],
        },
    }


class ConfigTests(unittest.TestCase):
    def test_loads_all_known_projects(self):
        cfg = load_config(CONFIG_PATH)
        names = [p.name for p in cfg.projects]
        self.assertEqual(
            set(names),
            {"agent-ops-dashboard", "Financial", "MonitorSelf", "soe"},
        )
        self.assertTrue(cfg.loki.url.startswith("http"))
        self.assertGreater(cfg.loki.query_limit, 0)

    def test_env_overrides_loki_url(self):
        with patch.dict("os.environ", {"LOKI_URL": "http://loki.example:3100"}):
            cfg = load_config(CONFIG_PATH)
        self.assertEqual(cfg.loki.url, "http://loki.example:3100")


class AnalyzerTests(unittest.TestCase):
    def test_summarize_actions_error_spike(self):
        entries = tuple(
            LogEntry(
                ts_ns=i,
                line=json.dumps({"level": "error", "error_type": "HTTP500"}),
                labels={"app": "Financial"},
            )
            for i in range(10)
        ) + tuple(
            LogEntry(
                ts_ns=100 + i,
                line=json.dumps({"level": "info", "action": "click"}),
                labels={"app": "Financial"},
            )
            for i in range(5)
        )
        result = QueryResult(query="q", entries=entries, truncated=False)
        stats = summarize_actions(result)
        self.assertEqual(stats.total, 15)
        self.assertEqual(stats.errors, 10)
        self.assertAlmostEqual(stats.error_rate, 10 / 15, places=4)
        self.assertEqual(stats.top_errors[0][0], "HTTP500")

    def test_summarize_performance_percentiles(self):
        entries = tuple(
            LogEntry(
                ts_ns=i,
                line=json.dumps({"action": "load", "duration_ms": float(i)}),
                labels={},
            )
            for i in range(1, 101)
        )
        result = QueryResult(query="q", entries=entries, truncated=False)
        perf = summarize_performance(result)
        self.assertEqual(perf.samples, 100)
        self.assertGreaterEqual(perf.p95_ms, 90)
        self.assertLessEqual(perf.p95_ms, 100)
        self.assertEqual(perf.slowest_ops[0][0], "load")


class LokiClientParseTests(unittest.TestCase):
    def test_query_range_parses_payload(self):
        client = LokiClient(base_url="http://localhost:3100", timeout=5)

        class FakeResp:
            status_code = 200

            def json(self_inner):  # noqa: N802
                return _fake_loki_payload(
                    [
                        (1_700_000_000_000_000_000, '{"action":"click","duration_ms":10}'),
                        (1_700_000_001_000_000_000, '{"level":"error","error_type":"X"}'),
                    ]
                )

        with patch.object(client._session, "get", return_value=FakeResp()):
            result = client.query_range('{app="Financial"}', "5m", limit=10)
        self.assertEqual(len(result.entries), 2)
        self.assertFalse(result.truncated)


class EndToEndReportTests(unittest.TestCase):
    def test_dry_run_produces_report(self):
        cfg = load_config(CONFIG_PATH)
        project = cfg.projects[0]
        report = _analyze_project(None, cfg, project, dry_run=True)
        md = format_report(report)
        self.assertIn(project.name, md)
        self.assertIn("Findings", md)
        # Dry run with zero data → triggers the low-severity "no telemetry" anomaly.
        self.assertTrue(report.findings)
        brief = format_remediation_brief(report)
        self.assertIn(project.repo_path, brief)

    def test_write_report_files(self):
        import tempfile

        cfg = load_config(CONFIG_PATH)
        project = cfg.projects[1]
        report = _analyze_project(None, cfg, project, dry_run=True)
        with tempfile.TemporaryDirectory() as tmp:
            rp, bp = write_report_files(report, output_dir=Path(tmp))
            self.assertTrue(rp.exists())
            self.assertIn(project.name, rp.read_text())
            if bp is not None:
                self.assertTrue(bp.exists())

    def test_arg_parser_help(self):
        # Must be constructible — underpins the --help smoke check.
        parser = build_arg_parser()
        self.assertIn("project-analyzer", parser.prog)


if __name__ == "__main__":
    unittest.main(verbosity=2)
