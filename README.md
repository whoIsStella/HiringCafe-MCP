# HiringCafe MCP

A narrow, read-only MCP interface for finding jobs through the unofficial `hiringcafe-cli`. Four tools, capped search results, and no generic shell or account-mutation endpoint.

**Read-only adapter.** The upstream client is pinned to
`0.1.5`; this is not an official HiringCafe integration.

## Interface

| Tool | Access |
| --- | --- |
| `search_jobs(query, pages=1, no_cache=false)` | Search, at most five pages; compact output |
| `count_jobs(query)` | Search count |
| `show_job(object_id)` | One job's full details |
| `list_saved_jobs()` | Authenticated user's saved-job board, read-only |

The server constructs CLI argument lists without invoking a shell. CLI failures
become structured diagnostics. There are no save, stage, remove, application,
or arbitrary command tools.

## Run and test

Requires Python 3.11+ and `uv`.

```bash
uv sync
uv run python -m unittest discover -s tests -v
uv run hiringcafe-mcp
```

The server uses stdio by default. For Codex:

```toml
[mcp_servers.hiringcafe]
command = "uv"
args = ["run", "--project", "/ABSOLUTE/PATH/HiringCafe-MCP", "hiringcafe-mcp"]
startup_timeout_ms = 20000
```

## Optional account access

Only `list_saved_jobs()` requires HiringCafe authentication:

```bash
uv run hiringcafe auth login --email YOU@example.com
uv run hiringcafe saved-jobs list --json
```

The upstream CLI owns credential storage. Keep its session files out of the
repository and treat the server's host account as trusted.

## HTTP and deployment

```bash
MCP_TRANSPORT=streamable-http MCP_HOST=127.0.0.1 MCP_PORT=8000 \
  uv run hiringcafe-mcp
```

Endpoint: `http://127.0.0.1:8000/mcp`. `Dockerfile.vercel` installs the
package and runs unit tests before producing the image; `PORT` overrides
`MCP_PORT` when supplied.

HTTP mode does not implement authentication here. Keep it local or put it behind
an authenticated service before exposing account-backed state. Read-only does
not mean private.

Upstream availability, authentication, and response shape can change. These
tests do not establish that HiringCafe's live service is reachable. Use results
for discovery and check consequential details on the employer's own posting.
