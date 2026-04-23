# LokiKit Python SDK

Python logging handler that ships structured JSON logs to Grafana Loki.
Works with any Python 3.10+ project — FastAPI, Django, CLI tools, scripts.

## Install

```bash
pip install -e sdks/python/          # from LokiKit root
# or
pip install lokikit                  # once published
```

## Quick Start

```python
import logging
from lokikit import LokiHandler

handler = LokiHandler(
    endpoint="http://localhost:3100/loki/api/v1/push",
    labels={"app": "my-api", "env": "dev"},
    batch_size=20,
    flush_interval=5.0,
)

logger = logging.getLogger("my-api")
logger.addHandler(handler)
logger.setLevel(logging.DEBUG)

logger.info("Server started", extra={"port": 8000})
logger.error("Request failed", extra={"status": 500, "path": "/api/data"})
```

## FastAPI Integration

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from lokikit import LokiHandler
import logging

handler = LokiHandler(
    labels={"app": "my-fastapi", "env": "dev"},
)
logging.getLogger().addHandler(handler)
logging.getLogger().setLevel(logging.INFO)

@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    handler.close()  # flush on shutdown

app = FastAPI(lifespan=lifespan)
```

## Low-Level Client

```python
from lokikit import LokiClient

client = LokiClient(
    labels={"app": "script", "env": "dev"},
    batch_size=50,
)
client.push('{"event": "processed", "count": 42}')
client.close()  # flush remaining
```

## Async Support

```python
from lokikit import LokiClient

client = LokiClient(labels={"app": "async-worker"})
await client.apush("async log line")
await client.aflush()  # uses aiohttp
```

## Configuration

| Parameter | Default | Description |
|---|---|---|
| `endpoint` | `http://localhost:3100/loki/api/v1/push` | Loki push URL |
| `labels` | `{}` | Static labels for the log stream |
| `batch_size` | `20` | Flush after N buffered entries |
| `flush_interval` | `5.0` | Auto-flush interval in seconds |
| `token` | `None` | Bearer token for authenticated Loki |

## Environment Variables

| Variable | Purpose |
|---|---|
| `LOKI_ENDPOINT` | Override default endpoint |
| `LOKI_TOKEN` | Bearer token |
