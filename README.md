# HiringCafe MCP

HiringCafe MCP lets job seekers search HiringCafe from an MCP-compatible client,
including Codex. It wraps the unofficial `hiringcafe-cli` package and provides
read-only search, counts, job details, and access to an authenticated user's
saved-job board. It cannot save jobs, change stages, or submit applications.

## Get started

Requires Python 3.11 or newer and `uv`.

```sh
git clone https://github.com/whoIsStella/HiringCafe-MCP.git
cd HiringCafe-MCP
uv sync
uv run hiringcafe-mcp
```

The server uses stdio by default and waits for an MCP client; it is not an
interactive job-search terminal. For Codex, add the following to
`~/.codex/config.toml`, replacing the project path:

```toml
[mcp_servers.hiringcafe]
command = "uv"
args = ["run", "--project", "/ABSOLUTE/PATH/HiringCafe-MCP", "hiringcafe-mcp"]
startup_timeout_ms = 20000
```

Restart or reconnect the client, then use `search_jobs` with a query such as
`backend software engineer` and `pages=1`. Full details are available through
`show_job` using an ID from a search result. Check important details on the
employer's own posting before applying.

## Tools and input limits

| Tool | Inputs and behavior |
| --- | --- |
| `search_jobs(query, pages=1, no_cache=false)` | Nonempty query; requests 1–5 pages from the upstream CLI. |
| `count_jobs(query)` | Nonempty query; returns the upstream search count. |
| `show_job(object_id)` | Nonempty job ID; returns the upstream job details. |
| `list_saved_jobs()` | Reads the saved-job board using credentials available to the server's host account. |

Queries and IDs have surrounding whitespace removed. CLI commands use argument
lists without a shell. Search has a 90-second timeout; the other commands have
a 60-second timeout.

Search compaction keeps at most 20 entries when the upstream JSON has a top-level
`jobs` list and omits large fields such as descriptions. Other response shapes
pass through unchanged, so this is not a guaranteed response-size limit. The
adapter depends on the CLI's pagination options and upstream JSON format.

## Optional account access

To access saved jobs, authenticate the same host account that runs the server:

```sh
uv run hiringcafe auth login --email YOU@example.com
uv run hiringcafe saved-jobs list --json
```

The upstream CLI owns credential storage. Keep its credential files private and
outside the repository. Unauthenticated search still depends on upstream
availability and access controls.

## HTTP access

```sh
MCP_TRANSPORT=streamable-http MCP_HOST=127.0.0.1 MCP_PORT=8000 \
  uv run hiringcafe-mcp
```

Connect the client to `http://127.0.0.1:8000/mcp`. `PORT` overrides `MCP_PORT` if
both are set. `Dockerfile.vercel` remains available for self-hosted containers.

Set `MCP_ACCESS_TOKEN` to require `Authorization: Bearer <token>` on MCP requests.
Vercel requires this variable and rejects requests if it is missing. Local HTTP
can run without it; keep that listener private. All authenticated clients share
the host's HiringCafe account. This is bearer authentication, not an OAuth server.
Clients that cannot send a bearer header should use the local stdio setup.

The HTTP endpoint accepts POST requests and returns JSON. GET returns 405 instead
of opening an idle event stream. Tool discovery and the four read-only tools are
available without a persistent session. The maximum request body is 64 KiB.

## Vercel deployment

`vercel.json` selects a native Python Function instead of the container preset.
The `/mcp` route invokes `api/index.py`. `/`, `/health`, and `/robots.txt` are static
files; health checks confirm deployment availability, not upstream HiringCafe
availability. Unknown paths return a static 404. No cron or background jobs run.
The function duration limit is 120 seconds, leaving room for the existing
90-second CLI deadline. Hobby Fluid memory is controlled by Vercel, so there is
no memory override in this configuration.

Repeated public reads use a process-local cache for 60 seconds. Errors are kept
for 15 seconds to damp repeated failures. Concurrent identical reads share one
CLI call. At most two distinct CLI calls run per process; additional work returns
`ok: false` with `retry_after: 5`. The cache holds at most 128 entries and 4 MiB
of serialized values and keys. `no_cache=true` bypasses retained search results.
Saved-job responses are never retained. Caches and concurrency limits are per
process, not global across Vercel instances.

There are no recurring paid dependencies. Remote tool calls still consume CPU
and provisioned memory while they run, including upstream network waits. Free
tier viability depends on request volume and upstream latency. For workloads
that exceed the allowance, use the existing local stdio server: all four tools
then run on the client machine with no Vercel compute usage.

## Troubleshooting

- **Executable not found:** run `uv sync` and launch through `uv run` so the
  pinned `hiringcafe-cli==0.1.5` executable is on the server's path.
- **`ok: false` result:** inspect `error`, `exit_code`, and `stderr` in the tool
  response. A successful MCP connection does not imply a successful job search.
- **Invalid arguments or search state:** use a nonempty query and a page count
  from 1 to 5. If stderr reports an unsupported CLI option, the adapter and CLI
  are incompatible; changing the client connection does not resolve that error.
- **HTTP 403, challenge, or rate limit:** the upstream service can refuse
  server-side requests. This adapter has no browser fallback or challenge solver.
  Use HiringCafe's normal website when access is blocked; repeated retries do
  not establish that a search is empty.
- **Authentication required or rejected:** run the optional login command under
  the server's host account and reconnect after re-authentication.
- **Timeout or non-JSON output:** check the diagnostic and try the corresponding
  command with `uv run hiringcafe` to distinguish CLI failures from connection
  failures. Search and other CLI commands have the timeouts listed above.

This is not an official HiringCafe integration. Upstream APIs, access controls,
and response formats can change, and results may be incomplete or stale.
