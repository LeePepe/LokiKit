"""logging.Handler subclass that ships structured JSON logs to Loki."""

from __future__ import annotations

import json
import logging
from typing import Any

from lokikit.client import LokiClient, DEFAULT_ENDPOINT


class LokiHandler(logging.Handler):
    """Drop-in logging handler that pushes structured JSON to Grafana Loki.

    Usage::

        import logging
        from lokikit import LokiHandler

        handler = LokiHandler(
            endpoint="http://localhost:3100/loki/api/v1/push",
            labels={"app": "my-api", "env": "dev"},
        )
        logger = logging.getLogger("my-api")
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)
        logger.info("Server started", extra={"port": 8000})
    """

    def __init__(
        self,
        endpoint: str = DEFAULT_ENDPOINT,
        labels: dict[str, str] | None = None,
        batch_size: int = 20,
        flush_interval: float = 5.0,
        token: str | None = None,
        level: int = logging.NOTSET,
    ) -> None:
        super().__init__(level=level)
        self._client = LokiClient(
            endpoint=endpoint,
            labels=labels,
            batch_size=batch_size,
            flush_interval=flush_interval,
            token=token,
        )

    def emit(self, record: logging.LogRecord) -> None:
        try:
            entry = self._format_record(record)
            self._client.push(json.dumps(entry, default=str))
        except Exception:
            self.handleError(record)

    def flush(self) -> None:
        self._client.flush()

    def close(self) -> None:
        self._client.close()
        super().close()

    @property
    def client(self) -> LokiClient:
        return self._client

    @staticmethod
    def _format_record(record: logging.LogRecord) -> dict[str, Any]:
        entry: dict[str, Any] = {
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "timestamp": record.created,
            "module": record.module,
            "funcName": record.funcName,
            "lineno": record.lineno,
        }
        # Merge extra fields (anything not in standard LogRecord)
        standard = logging.LogRecord("", 0, "", 0, "", (), None).__dict__.keys()
        for k, v in record.__dict__.items():
            if k not in standard and k not in entry:
                entry[k] = v
        return entry
