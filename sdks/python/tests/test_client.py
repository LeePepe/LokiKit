"""Tests for LokiClient."""

import json
import threading
from unittest.mock import patch, MagicMock

import pytest

from lokikit.client import LokiClient


class TestLokiClient:
    def test_build_body(self):
        client = LokiClient(labels={"app": "test"}, flush_interval=999)
        body = client._build_body([("1000", "hello"), ("2000", "world")])
        assert body == {
            "streams": [
                {
                    "stream": {"app": "test"},
                    "values": [["1000", "hello"], ["2000", "world"]],
                }
            ]
        }
        client.close()

    def test_push_buffers(self):
        client = LokiClient(batch_size=100, flush_interval=999)
        client.push("line1")
        client.push("line2")
        assert len(client._buffer) == 2
        client.close()

    def test_flush_clears_buffer(self):
        client = LokiClient(batch_size=100, flush_interval=999)
        client.push("line1")
        # Mock urllib so no actual HTTP call
        with patch("lokikit.client.urllib.request.urlopen"):
            client.flush()
        assert len(client._buffer) == 0
        client.close()

    def test_batch_size_triggers_flush(self):
        client = LokiClient(batch_size=2, flush_interval=999)
        with patch("lokikit.client.urllib.request.urlopen") as mock_open:
            client.push("a")
            assert mock_open.call_count == 0
            client.push("b")  # hits batch_size=2
            assert mock_open.call_count == 1
        client.close()

    def test_close_flushes(self):
        client = LokiClient(batch_size=100, flush_interval=999)
        client.push("leftover")
        with patch("lokikit.client.urllib.request.urlopen") as mock_open:
            client.close()
            assert mock_open.call_count == 1

    def test_token_header(self):
        client = LokiClient(batch_size=1, flush_interval=999, token="secret")
        with patch("lokikit.client.urllib.request.urlopen") as mock_open:
            client.push("line")
            req = mock_open.call_args[0][0]
            assert req.get_header("Authorization") == "Bearer secret"
        client.close()

    def test_empty_flush_no_http(self):
        client = LokiClient(flush_interval=999)
        with patch("lokikit.client.urllib.request.urlopen") as mock_open:
            client.flush()
            assert mock_open.call_count == 0
        client.close()
