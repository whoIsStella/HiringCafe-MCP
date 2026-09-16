# HiringCafe MCP (read-only)

Small MCP adapter around the unofficial `hiringcafe-cli` package. It deliberately exposes only read/search operations:

- `search_jobs(query, pages=1, no_cache=false)`
- `count_jobs(query)`
- `show_job(object_id)`
- `list_saved_jobs()` (requires HiringCafe authentication)

No save/stage/remove mutation tools are exposed in this first version.

## Local requirements

- Python 3.11+
- `uv`
- A HiringCafe account only if you want `list_saved_jobs`

## Install / verify locally

```bash
uv sync
uv run hiringcafe search "backend software engineer" --page 0 --json
uv run python -m unittest discover -s tests -v
```

`hiringcafe-cli` is pinned to `0.1.5` because it is an unofficial beta client and upstream APIs can change.

## Optional: authenticate your HiringCafe account

```bash
uv run hiringcafe auth login --email YOU@example.com
uv run hiringcafe saved-jobs list --json
```

The password is read interactively by `hiringcafe-cli`. Do not put credentials in this project, Codex config, Git, or prompts. The CLI stores its refresh token under `~/.config/hiringcafe-cli/session.json` with owner-only permissions.

## Connect to Codex locally

Add this to `~/.codex/config.toml` after replacing the path:

```toml
[mcp_servers.hiringcafe]
command = "uv"
args = ["run", "--project", "/ABSOLUTE/PATH/HiringCafe-MCP", "hiringcafe-mcp"]
startup_timeout_ms = 20000
```

## Run as Streamable HTTP locally

```bash
MCP_TRANSPORT=streamable-http MCP_HOST=127.0.0.1 MCP_PORT=8000 \
  uv run hiringcafe-mcp
```

Endpoint: `http://127.0.0.1:8000/mcp`

## Deploy to Vercel

This repository includes `Dockerfile.vercel`. Vercel builds the Python service into a custom container and supplies `$PORT`; the server binds to `0.0.0.0:$PORT` in HTTP mode.

1. Import this GitHub repository into Vercel.
2. Deploy it without adding HiringCafe credentials.
3. Verify the remote MCP endpoint at `https://<deployment>/mcp`.
4. Add authentication before connecting the endpoint to ChatGPT or enabling account-backed saved-job access.

The Docker build runs the adapter unit tests before producing the image.

## Security boundary

- Read-only MCP tools only.
- No HiringCafe username/password/session token is committed.
- Search pages capped at 5 to avoid accidental high-volume scraping.
- No shell invocation; CLI calls use an argv list.
- CLI exit codes are translated into useful MCP errors.
- The remote endpoint should not be treated as private merely because the tools are read-only. Add access control before using authenticated HiringCafe state.

## Design notes

HiringCafe does not provide an official self-service public API for this integration, so this adapter depends on the unofficial `hiringcafe-cli` package. Returned jobs are discovery evidence; consequential details should still be verified against the employer's canonical posting.
