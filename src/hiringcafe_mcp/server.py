from __future__ import annotations

import os
from typing import Any

from mcp.server import MCPServer
from mcp.types import ToolAnnotations

from .cli import run_json

mcp = MCPServer(
    "HiringCafe",
    instructions=(
        "Read-only access to HiringCafe via hiringcafe-cli. Treat returned job data as "
        "discovery evidence and verify consequential details against the employer's posting."
    ),
)

READ_ONLY = ToolAnnotations(read_only_hint=True, idempotent_hint=True)


@mcp.tool(
    title="Search HiringCafe jobs",
    description="Search HiringCafe and return structured job results. Pages are capped at 5.",
    annotations=READ_ONLY,
)
def search_jobs(query: str, pages: int = 1, no_cache: bool = False) -> Any:
    query = query.strip()
    if not query:
        raise ValueError("query must not be empty")
    if not 1 <= pages <= 5:
        raise ValueError("pages must be between 1 and 5")
    args = ["search", query, "--pages", str(pages), "--json"]
    if no_cache:
        args.append("--no-cache")
    return run_json(args, timeout=90)


@mcp.tool(
    title="Count HiringCafe jobs",
    description="Return the machine-readable result count for a HiringCafe search.",
    annotations=READ_ONLY,
)
def count_jobs(query: str) -> Any:
    query = query.strip()
    if not query:
        raise ValueError("query must not be empty")
    return run_json(["count", query, "--json"])


@mcp.tool(
    title="Show HiringCafe job",
    description="Retrieve full structured details for one HiringCafe object ID.",
    annotations=READ_ONLY,
)
def show_job(object_id: str) -> Any:
    object_id = object_id.strip()
    if not object_id:
        raise ValueError("object_id must not be empty")
    return run_json(["job", "show", object_id, "--json"])


@mcp.tool(
    title="List HiringCafe saved jobs",
    description=(
        "List the authenticated user's HiringCafe saved-job board and stages. "
        "Requires prior hiringcafe auth login/import on this machine."
    ),
    annotations=READ_ONLY,
)
def list_saved_jobs() -> Any:
    return run_json(["saved-jobs", "list", "--json"])


def main() -> None:
    transport = os.getenv("MCP_TRANSPORT", "stdio").strip().lower()
    if transport == "stdio":
        mcp.run()
        return
    if transport == "streamable-http":
        host = os.getenv("MCP_HOST", "127.0.0.1")
        port = int(os.getenv("PORT", os.getenv("MCP_PORT", "80")))
        mcp.run(
            transport="streamable-http",
            host=host,
            port=port,
            streamable_http_path="/mcp",
            stateless_http=True,
            json_response=True,
        )
        return
    raise ValueError("MCP_TRANSPORT must be 'stdio' or 'streamable-http'")


if __name__ == "__main__":
    main()
