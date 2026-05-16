# LokiKit Onboarding Checklist

Steps to integrate any new project with the LokiKit telemetry stack.

## 1. Detect Stack

- [ ] Identify project language/framework:
  - **Swift/macOS** → Swift SDK (`sdks/swift/`)
  - **Python/FastAPI/Django** → Python SDK (`sdks/python/`)
  - **TypeScript/React/Node** → Web SDK (`sdks/web/`)
- [ ] Check if project already has logging (look for `logging`, `console.log`, `os_log`)

## 2. Ensure Stack Is Running

- [ ] LokiKit stack is up: `docker compose -f ~/Development/LokiKit/stack/docker-compose.yml up -d`
- [ ] Verify Loki: `curl -s http://localhost:3100/ready` → `ready`
- [ ] Verify Grafana: open http://localhost:3010 (admin / telemetry)

## 3. Install SDK

### Python
```bash
pip install -e ~/Development/LokiKit/sdks/python/
```

### Web (TypeScript/Node)
```bash
npm install --save ~/Development/LokiKit/sdks/web/
# or add to package.json: "@leepepe/loki-web": "file:../../LokiKit/sdks/web"
```

### Swift
```swift
// Package.swift
.package(path: "~/Development/LokiKit/sdks/swift")
```

## 4. Configure

- [ ] Set labels: `{app: "<project-name>", env: "dev"}`
- [ ] Set endpoint: `http://localhost:3100/loki/api/v1/push`
- [ ] Add handler/logger initialization at app startup
- [ ] Add cleanup/flush at app shutdown

## 5. Add Grafana Dashboard

- [ ] Create or copy a dashboard JSON
- [ ] Place in `~/Development/LokiKit/stack/grafana/dashboards/<project>.json`
- [ ] Verify it appears in Grafana

## 6. Verify Integration

- [ ] Run the project and trigger some logs
- [ ] Query in Grafana: `{app="<project-name>"}`
- [ ] Confirm logs appear with correct labels and structure

## 7. Update Registry

- [ ] Add project to the "Projects Using This Stack" table in `~/Development/LokiKit/README.md`
- [ ] Run `python scripts/audit-projects.py` to verify detection

---

## Known Projects & Status

| Project | Stack | SDK Needed | Status |
|---|---|---|---|
| VoxPocket | Swift/macOS | Swift | ✅ Integrated |
| Financial | FastAPI/React | Python + Web | ✅ Has dashboard |
| soe/MacMetric | Swift/macOS | Swift | ⏳ Needs integration |
| agent-ops-dashboard | FastAPI/React | Python + Web | ⏳ Needs integration |
| NameForge | React/Node | Web | ⏳ Needs integration |
| MonitorSelf | FastAPI/React | Python + Web | ⏳ Needs integration |
