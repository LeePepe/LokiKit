# loki-telemetry-stack

Shared local telemetry backend for development — Loki + Grafana, deployable with a single command.

## Quick Start

```bash
cp .env.example .env        # optional: customize ports/password
docker compose up -d
```

- **Grafana**: http://localhost:3010 (admin / telemetry)
- **Loki push endpoint**: http://localhost:3100/loki/api/v1/push

## Configuration

Copy `.env.example` to `.env` and adjust as needed:

| Variable | Default | Description |
|---|---|---|
| `LOKI_PORT` | `3100` | Loki HTTP port |
| `GRAFANA_PORT` | `3010` | Grafana HTTP port |
| `GRAFANA_USER` | `admin` | Grafana admin username |
| `GRAFANA_PASSWORD` | `telemetry` | Grafana admin password |

## Adding a Dashboard for Your Project

1. Export your dashboard JSON from Grafana (Dashboard → Share → Export → Save to file)
2. Place the file in `grafana/dashboards/<your-project>.json`
3. Restart Grafana: `docker compose restart grafana`

Grafana polls `grafana/dashboards/` every 30 seconds, so live edits appear automatically.

## Sending Logs from Your App

Push logs to Loki using the standard push API:

```
POST http://localhost:3100/loki/api/v1/push
```

### Swift (LokiTelemetryService)

Set the environment variable before launching your app:

```bash
export LOKI_ENDPOINT=http://localhost:3100/loki/api/v1/push
```

### Environment Variables Expected by Clients

| Variable | Purpose |
|---|---|
| `LOKI_ENDPOINT` | Loki push URL |
| `LOKI_TOKEN` | Bearer token (leave unset for local dev) |

## Projects Using This Stack

| Project | Dashboard | Log label |
|---|---|---|
| VoxPocket (Swift/macOS) | `grafana/dashboards/voxpocket.json` | `{app="VoxPocket"}` |
| Financial (FastAPI/React) | `grafana/dashboards/financial.json` | `{app="Financial"}` |
