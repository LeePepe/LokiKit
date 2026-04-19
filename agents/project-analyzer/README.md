# project-analyzer

A per-project telemetry analyzer for this Loki stack. For every configured project
(currently `agent-ops-dashboard`, `Financial`, `MonitorSelf`, `soe`) it queries Loki
for recent `user_action` and `performance` streams, detects common issues, and writes
a markdown report plus (when issues are found) a remediation brief intended to be
handed to that repo's team-lead.

## What it detects

| Kind              | Heuristic                                                                        |
|-------------------|----------------------------------------------------------------------------------|
| `error_spike`     | Error rate ≥ `thresholds.error_rate_spike` **and** errors ≥ `error_count_min`.   |
| `regression`      | Recent p95 latency ≥ `perf_regression_ratio` × baseline p95.                     |
| `silent_failure`  | Recent action volume ≤ `silent_failure_ratio` × baseline (when baseline ≥ min). |
| `anomaly`         | No telemetry in either recent or baseline window.                                |

All thresholds live in [`config.yaml`](./config.yaml); tune per your signal/noise.

## Install

```bash
python3 -m venv .venv && . .venv/bin/activate
pip install -r agents/project-analyzer/requirements.txt
```

## Usage

```bash
# All projects, using config defaults
python3 agents/project-analyzer/run.py

# A single project
python3 agents/project-analyzer/run.py --project Financial

# Override Loki URL at the CLI
python3 agents/project-analyzer/run.py --loki-url http://loki.local:3100

# Dry run (no network; useful for CI and smoke testing)
python3 agents/project-analyzer/run.py --dry-run -v

# See all flags
python3 agents/project-analyzer/run.py --help
```

### Environment variables

| Variable     | Purpose                                          |
|--------------|--------------------------------------------------|
| `LOKI_URL`   | Overrides `loki.url` in config. Never committed. |
| `LOKI_TOKEN` | Optional bearer token for Loki (never committed).|

### Exit codes

| Code | Meaning                                       |
|------|-----------------------------------------------|
| `0`  | Success, no findings.                         |
| `2`  | Success, one or more findings written.        |
| `3`  | Config error (bad YAML, unknown project, …).  |
| `4`  | Runtime error (Loki unreachable, etc.).       |

## Output

Reports are written to:

```
agents/project-analyzer/reports/<project>/<YYYY-MM-DD>.md
agents/project-analyzer/reports/<project>/<YYYY-MM-DD>.remediation.md  # only if issues
```

Running again on the same day overwrites that day's files (idempotent).

## Tests

```bash
python3 -m pytest agents/project-analyzer/tests/ -q
# or, without pytest:
python3 agents/project-analyzer/tests/test_smoke.py
```

The smoke test covers config loading, error-spike + performance summarization,
Loki payload parsing (mocked), and end-to-end markdown report + remediation
rendering via the `--dry-run` code path.

## Scheduling

### Hermes cron (`~/.hermes/cron.yaml`)

```yaml
jobs:
  - name: loki-project-analyzer
    schedule: "*/30 * * * *"   # every 30 minutes
    command: /usr/bin/env bash -lc 'cd ~/Development/loki-telemetry-stack && LOKI_URL=http://localhost:3100 python3 agents/project-analyzer/run.py'
    log: ~/Library/Logs/loki-project-analyzer.log
```

### macOS `launchd`

Save as `~/Library/LaunchAgents/com.leepepe.loki-project-analyzer.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple Computer//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key><string>com.leepepe.loki-project-analyzer</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/env</string>
        <string>bash</string>
        <string>-lc</string>
        <string>cd ~/Development/loki-telemetry-stack &amp;&amp; python3 agents/project-analyzer/run.py</string>
    </array>
    <key>EnvironmentVariables</key>
    <dict>
        <key>LOKI_URL</key><string>http://localhost:3100</string>
    </dict>
    <key>StartInterval</key><integer>1800</integer>
    <key>StandardOutPath</key><string>/tmp/loki-project-analyzer.out.log</string>
    <key>StandardErrorPath</key><string>/tmp/loki-project-analyzer.err.log</string>
    <key>RunAtLoad</key><true/>
</dict>
</plist>
```

Load it:

```bash
launchctl load ~/Library/LaunchAgents/com.leepepe.loki-project-analyzer.plist
launchctl start com.leepepe.loki-project-analyzer
```

## Design notes

- **Immutability:** all config / stats / reports are frozen dataclasses or tuples;
  overrides are applied via `dataclasses.replace`, never mutation.
- **Many small files:** split across `lib/config.py`, `lib/loki_client.py`,
  `lib/analyzer.py`, `lib/report.py` — each under ~250 lines, single-responsibility.
- **No secrets on disk:** bearer tokens come from `LOKI_TOKEN` env only.
- **Fails fast:** config is validated at load; exit codes distinguish config vs runtime.
