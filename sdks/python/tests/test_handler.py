"""Tests for LokiHandler."""

import json
import logging
from unittest.mock import patch

from lokikit.handler import LokiHandler


class TestLokiHandler:
    def test_handler_emits_json(self):
        handler = LokiHandler(
            labels={"app": "test"},
            batch_size=100,
            flush_interval=999,
        )
        logger = logging.getLogger("test.lokikit")
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)

        logger.info("hello world")

        assert len(handler.client._buffer) == 1
        _, line = handler.client._buffer[0]
        parsed = json.loads(line)
        assert parsed["message"] == "hello world"
        assert parsed["level"] == "INFO"

        logger.removeHandler(handler)
        handler.close()

    def test_handler_extra_fields(self):
        handler = LokiHandler(batch_size=100, flush_interval=999)
        logger = logging.getLogger("test.extra")
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)

        logger.info("req", extra={"request_id": "abc-123"})

        _, line = handler.client._buffer[0]
        parsed = json.loads(line)
        assert parsed["request_id"] == "abc-123"

        logger.removeHandler(handler)
        handler.close()

    def test_handler_flush_and_close(self):
        handler = LokiHandler(batch_size=100, flush_interval=999)
        logger = logging.getLogger("test.close")
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)

        logger.warning("important")

        with patch("lokikit.client.urllib.request.urlopen"):
            handler.close()

        assert len(handler.client._buffer) == 0
        logger.removeHandler(handler)

    def test_format_record_structure(self):
        record = logging.LogRecord(
            name="test", level=logging.ERROR, pathname="test.py",
            lineno=42, msg="boom", args=(), exc_info=None,
        )
        entry = LokiHandler._format_record(record)
        assert entry["level"] == "ERROR"
        assert entry["message"] == "boom"
        assert entry["lineno"] == 42
