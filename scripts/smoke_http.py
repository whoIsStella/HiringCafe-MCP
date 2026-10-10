"""Validate an HTTP deployment without logging bearer tokens or saved jobs."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
import os
from urllib.error import HTTPError
from urllib.request import Request, urlopen


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("endpoint", help="Full /mcp URL")
    parser.add_argument("--live-query", help="Optional real, read-only count query")
    args = parser.parse_args()
    token = os.environ.get("MCP_ACCESS_TOKEN")
    if not token:
        parser.error("Set MCP_ACCESS_TOKEN in the environment")

    def request(method="POST", payload=None, authenticated=True):
        headers = {"Content-Type": "application/json",
                   "Accept": "application/json, text/event-stream"}
        if authenticated:
            headers["Authorization"] = "Bearer " + token
        req = Request(args.endpoint, method=method, headers=headers,
                      data=json.dumps(payload).encode() if payload is not None else None)
        try:
            with urlopen(req, timeout=120) as response:
                return response.status, response.read()
        except HTTPError as response:
            return response.code, response.read()

    def rpc(method, params=None):
        payload = {"jsonrpc": "2.0", "id": 1, "method": method}
        if params is not None:
            payload["params"] = params
        status, body = request(payload=payload)
        if status != 200:
            raise RuntimeError(f"{method}: expected HTTP 200, got {status}")
        response = json.loads(body)
        if "error" in response or "result" not in response:
            raise RuntimeError(f"{method}: invalid JSON-RPC response")
        return response["result"]

    assert request("GET")[0] == 405, "GET must not open an event stream"
    assert request(payload={}, authenticated=False)[0] == 401, "Unauthenticated POST must fail"
    assert request(payload={})[0] == 400, "Invalid JSON-RPC must fail"
    assert request(payload={"data": "x" * 65536})[0] == 413, "Oversized requests must fail"
    initialized = rpc("initialize", {
        "protocolVersion": "2025-03-26", "capabilities": {},
        "clientInfo": {"name": "hiringcafe-smoke", "version": "1"},
    })
    assert "serverInfo" in initialized
    expected = {"search_jobs", "count_jobs", "show_job", "list_saved_jobs"}
    with ThreadPoolExecutor(3) as pool:
        listings = list(pool.map(lambda _: rpc("tools/list"), range(3)))
    assert all({t["name"] for t in r["tools"]} == expected for r in listings)
    for name, arguments in [("search_jobs", {"query": ""}),
                            ("count_jobs", {"query": ""}),
                            ("show_job", {"object_id": ""})]:
        result = rpc("tools/call", {"name": name, "arguments": arguments})
        assert not result.get("isError"), f"{name}: transport/tool dispatch failure"
    print("PASS: bearer auth, body limits, initialize, concurrent discovery, tool dispatch, no SSE")
    if args.live_query:
        result = rpc("tools/call", {"name": "count_jobs",
                                  "arguments": {"query": args.live_query}})
        assert not result.get("isError"), "count_jobs: dispatch failure"
        structured = result.get("structuredContent")
        if structured is None:
            structured = json.loads(result["content"][0]["text"])
        if structured.get("ok") is False:
            print(f"UPSTREAM: structured diagnostic, exit code {structured.get('exit_code')}")
        else:
            print("PASS: live upstream count")


if __name__ == "__main__":
    main()
