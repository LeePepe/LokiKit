# loki-telemetry-stack

A monorepo containing the shared local telemetry backend (Loki + Grafana) and the client SDKs that push logs to it.

## Layout

```
loki-telemetry-stack/
├── stack/          # Docker Compose stack: Loki + Grafana + dashboards
├── sdks/
│   └── swift/      # LokiKit — Swift Package for iOS/macOS
└── .claude/        # Agent teamwork config
```

- `stack/` — deploy the backend with `docker compose -f stack/docker-compose.yml up -d`
- `sdks/swift/` — LokiKit Swift Package (SPM), consumable via `.package(path: "sdks/swift")` or a remote URL once published
- `sdks/web/` — _coming soon_ (added by a sibling task)
- A Claude Skill packaging is also planned

## Stack Quick Start

```bash
cp stack/.env.example stack/.env        # optional: customize ports/password
docker compose -f stack/docker-compose.yml --env-file stack/.env up -d
```

- Grafana: http://localhost:3010 (admin / telemetry)
- Loki push endpoint: http://localhost:3100/loki/api/v1/push

### Stack configuration

Copy `stack/.env.example` to `stack/.env` and adjust as needed:

| Variable | Default | Description |
|---|---|---|
| `LOKI_PORT` | `3100` | Loki HTTP port |
| `GRAFANA_PORT` | `3010` | Grafana HTTP port |
| `GRAFANA_USER` | `admin` | Grafana admin username |
| `GRAFANA_PASSWORD` | `telemetry` | Grafana admin password |

### Adding a dashboard

1. Export your dashboard JSON from Grafana (Dashboard → Share → Export → Save to file)
2. Place the file in `stack/grafana/dashboards/<your-project>.json`
3. Restart Grafana: `docker compose -f stack/docker-compose.yml restart grafana`

Grafana polls `stack/grafana/dashboards/` every 30 seconds, so live edits appear automatically.

## Swift SDK

See `sdks/swift/README.md`. Clients set:

```bash
export LOKI_ENDPOINT=http://localhost:3100/loki/api/v1/push
```

### Environment variables expected by clients

| Variable | Purpose |
|---|---|
| `LOKI_ENDPOINT` | Loki push URL |
| `LOKI_TOKEN`    | Bearer token (leave unset for local dev) |

## Web SDK

Coming soon under `sdks/web/`.

## Skill

A Claude Skill packaging is planned to make this stack one-shot installable for agent-driven setups.

## Projects Using This Stack

| Project | Dashboard | Log label |
|---|---|---|
| VoxPocket (Swift/macOS) | `stack/grafana/dashboards/voxpocket.json` | `{app="VoxPocket"}` |
| Financial (FastAPI/React) | `stack/grafana/dashboards/financial.json` | `{app="Financial"}` |
