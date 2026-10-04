import asyncio
import json
import os
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

from hiringcafe_mcp.cache import ReadCache
from hiringcafe_mcp.http import app


class CacheTests(unittest.TestCase):
    def test_hit_expiry_bypass_and_error_backoff(self):
        now = [0]
        cache = ReadCache(clock=lambda: now[0])
        calls = []
        def load():
            calls.append(1)
            return {"jobs": []}
        cache.run(("a",), load)
        cache.run(("a",), load)
        self.assertEqual(len(calls), 1)
        cache.run(("a",), load, bypass=True)
        self.assertEqual(len(calls), 2)
        now[0] = 61
        cache.run(("a",), load)
        self.assertEqual(len(calls), 3)
        cache.run(("error",), lambda: {"ok": False})
        self.assertEqual(cache.run(("error",), load), {"ok": False})
        now[0] += 16
        self.assertEqual(cache.run(("error",), load), {"jobs": []})

    def test_bounds_and_independent_results(self):
        cache = ReadCache(max_bytes=50)
        for i in range(10):
            cache.run((i,), lambda: {"value": "1234567890"})
        self.assertLessEqual(cache.size, 50)
        result = cache.run((9,), lambda: None)
        result["value"] = "changed"
        self.assertEqual(cache.run((9,), lambda: None)["value"], "1234567890")
        cache.run(("large",), lambda: "x" * 100)
        self.assertNotIn(("large",), cache.entries)

    def test_single_flight_and_worker_limit(self):
        cache = ReadCache()
        entered, release = threading.Event(), threading.Event()
        calls = []
        def load():
            calls.append(1)
            entered.set()
            self.assertTrue(release.wait(3))
            return {"ok": True}
        with ThreadPoolExecutor(4) as pool:
            first = pool.submit(cache.run, ("a",), load)
            self.assertTrue(entered.wait(2))
            duplicate = pool.submit(cache.run, ("a",), load)
            # Occupy the other slot to verify new unique work is rejected.
            self.assertTrue(cache.workers.acquire(blocking=False))
            self.assertEqual(cache.run(("b",), load)["retry_after"], 5)
            cache.workers.release()
            release.set()
            self.assertEqual(first.result(), duplicate.result())
        self.assertEqual(len(calls), 1)


async def request(method="POST", path="/mcp", body=None, token=None):
    payload = json.dumps(body).encode() if body is not None else b""
    sent = []
    headers = [(b"host", b"localhost:8000"), (b"content-type", b"application/json"),
               (b"accept", b"application/json, text/event-stream")]
    if token:
        headers.append((b"authorization", ("Bearer " + token).encode()))
    scope = {"type": "http", "asgi": {"version": "3.0"}, "http_version": "1.1",
             "scheme": "http", "path": path, "raw_path": path.encode(),
             "query_string": b"", "root_path": "", "method": method,
             "headers": headers, "client": ("127.0.0.1", 1234),
             "server": ("localhost", 8000)}
    async def receive():
        return {"type": "http.request", "body": payload, "more_body": False}
    async def send(message):
        sent.append(message)
    await asyncio.wait_for(app(scope, receive, send), timeout=3)
    status = next(m["status"] for m in sent if m["type"] == "http.response.start")
    response = b"".join(m.get("body", b"") for m in sent if m["type"] == "http.response.body")
    return status, response


class HttpTests(unittest.IsolatedAsyncioTestCase):
    async def test_get_never_opens_sse(self):
        self.assertEqual((await request("GET"))[0], 405)

    async def test_health_does_not_execute_cli(self):
        with patch("hiringcafe_mcp.server.run_json") as cli:
            self.assertEqual((await request("GET", "/health"))[0], 200)
            cli.assert_not_called()

    async def test_cloud_auth_fails_closed(self):
        with patch.dict(os.environ, {"VERCEL": "1", "MCP_ACCESS_TOKEN": ""}):
            self.assertEqual((await request())[0], 503)
        with patch.dict(os.environ, {"VERCEL": "1", "MCP_ACCESS_TOKEN": "secret"}):
            self.assertEqual((await request())[0], 401)
            self.assertEqual((await request(token="wrong"))[0], 401)

    async def test_mcp_flows_repeated_and_concurrent(self):
        with patch.dict(os.environ, {"VERCEL": "1", "MCP_ACCESS_TOKEN": "secret"}):
            initialize = {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {
                "protocolVersion": "2025-03-26", "capabilities": {},
                "clientInfo": {"name": "test", "version": "1"}}}
            status, body = await request(body=initialize, token="secret")
            self.assertEqual(status, 200, body)
            self.assertIn("serverInfo", json.loads(body)["result"])
            listing = {"jsonrpc": "2.0", "id": 2, "method": "tools/list"}
            for status, body in await asyncio.gather(*(request(body=listing, token="secret") for _ in range(3))):
                self.assertEqual(status, 200, body)
                self.assertEqual(len(json.loads(body)["result"]["tools"]), 4)
            for name, args in [("search_jobs", {"query": "test"}), ("count_jobs", {"query": "test"}),
                               ("show_job", {"object_id": "123"}), ("list_saved_jobs", {})]:
                with patch("hiringcafe_mcp.server.run_json", return_value={"ok": True}) as cli:
                    status, body = await request(body={"jsonrpc": "2.0", "id": 3, "method": "tools/call",
                        "params": {"name": name, "arguments": args}}, token="secret")
                    self.assertEqual(status, 200, body)
                    self.assertNotIn("error", json.loads(body))
                    cli.assert_called_once()
