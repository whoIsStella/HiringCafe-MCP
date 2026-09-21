# HiringCafe MCP

A small read-only MCP adapter for the unofficial `hiringcafe-cli` package.

It exposes:

- `search_jobs(query, pages=1, no_cache=false)`
- `count_jobs(query)`
- `show_job(object_id)`
- `list_saved_jobs()`, which requires HiringCafe authentication

There are no save, stage, remove, or other mutation tools.

## Requirements

- Python 3.11+
- `uv`
- a HiringCafe account only for `list_saved_jobs()`

## Install and test

```bash
uv sync
uv run hiringcafe search "backend software engineer" --page 0 --json
uv run python -m unittest discover -s tests -v
```

`hiringcafe-cli` is pinned to `0.1.5`. It is an unofficial beta client, so upstream behavior can change.

## Optional HiringCafe authentication

```bash
uv run hiringcafe auth login --email YOU@example.com
uv run hiringcafe saved-jobs list --json
```

The CLI reads the password interactively and stores its refresh token under `~/.config/hiringcafe-cli/session.json` with owner-only permissions.

Do not put HiringCafe credentials in this repository, Codex configuration, Git, or prompts.

## Codex configuration

Add the server to `~/.codex/config.toml`:

```toml
[mcp_servers.hiringcafe]
command = "uv"
args = ["run", "--project", "/ABSOLUTE/PATH/HiringCafe-MCP", "hiringcafe-mcp"]
startup_timeout_ms = 20000
```

## Streamable HTTP

```bash
MCP_TRANSPORT=streamable-http MCP_HOST=127.0.0.1 MCP_PORT=8000 \
  uv run hiringcafe-mcp
```

Local endpoint:

```text
http://127.0.0.1:8000/mcp
```

## Vercel deployment

The repository includes `Dockerfile.vercel`. Vercel supplies `$PORT`, and the service binds to `0.0.0.0:$PORT` in HTTP mode.

The Docker build runs the unit tests before producing the image.

A remote endpoint is not private just because the MCP tools are read-only. Add authentication before connecting a public deployment to account-backed HiringCafe state.

## Security boundaries

- read-only MCP tools
- no committed HiringCafe credentials or session tokens
- search requests capped at five pages
- no shell invocation
- CLI subprocesses use argument lists
- CLI failures are converted into MCP errors

## Notes

HiringCafe does not provide an official self-service public API for this integration. This adapter depends on the unofficial `hiringcafe-cli` package.

Use returned jobs for discovery. Verify consequential details against the employer's own posting.
