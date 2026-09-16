from __future__ import annotations

import os
from typing import Any

from mcp.server import MCPServer
from mcp.types import ToolAnnotations

from .cli import HiringCafeError, run_json

mcp = MCPServer(
    "HiringCafe",
    instructions=(
        "Read-only access to HiringCafe via hiringcafe-cli. Treat returned job data as "
        "discovery evidence and verify consequential details against the employer's posting."
    ),
)

READ_ONLY = ToolAnnotations(read_only_hint=True, idempotent_hint=True)


def _diagnostic_error(exc: HiringCafeError) -> dict[str, Any]:
    """Return a small structured error instead of an opaque MCP tool failure."""
    return {
        "ok": False,
        "error": exc.message,
        "exit_code": exc.exit_code,
        "stderr": exc.stderr.strip()[:4000],
    }


def _run(args: list[str], *, timeout: int = 60) -> Any:
    try:
        return run_json(args, timeout=timeout)
    except HiringCafeError as exc:
        return _diagnostic_error(exc)


def _compact_search(result: Any, max_jobs: int = 20) -> Any:
    """Keep search results small; full details are available through show_job."""
    if not isinstance(result, dict) or result.get("ok") is False:
        return result

    jobs = result.get("jobs")
    if not isinstance(jobs, list):
        return result

    preferred = (
        "objectID",
        "id",
        "title",
        "jobTitle",
        "company",
        "companyName",
        "location",
        "locations",
        "remote",
        "workplaceType",
        "salary",
        "salaryRange",
        "seniority",
        "experienceLevel",
        "datePosted",
        "postedAt",
        "url",
        "jobUrl",
        "applyUrl",
    )

    compact_jobs: list[Any] = []
    for job in jobs[:max_jobs]:
        if not isinstance(job, dict):
            compact_jobs.append(job)
            continue
        compact = {key: job[key] for key in preferred if key in job}
        compact_jobs.append(compact or {"objectID": job.get("objectID"), "title": job.get("title")})

    metadata = {key: value for key, value in result.items() if key != "jobs"}
    metadata.update(
        {
            "ok": True,
            "jobs": compact_jobs,
            "returned_jobs": len(compact_jobs),
            "available_in_page": len(jobs),
            "truncated": len(jobs) > len(compact_jobs),
        }
    )
    return metadata


@mcp.tool(
    title="Search HiringCafe jobs",
    description=(
        "Search HiringCafe and return a compact structured result set. Pages are capped at 5; "
        "use show_job for full details."
    ),
    annotations=READ_ONLY,
)
def search_jobs(query: str, pages: int = 1, no_cache: bool = False) -> Any:
    query = query.strip()
    if not query:
        return {"ok": False, "error": "query must not be empty"}
    if not 1 <= pages <= 5:
        return {"ok": False, "error": "pages must be between 1 and 5"}
    args = ["search", query, "--pages", str(pages), "--json"]
    if no_cache:
        args.append("--no-cache")
    return _compact_search(_run(args, timeout=90))


@mcp.tool(
    title="Count HiringCafe jobs",
    description="Return the machine-readable result count for a HiringCafe search.",
    annotations=READ_ONLY,
)
def count_jobs(query: str) -> Any:
    query = query.strip()
    if not query:
        return {"ok": False, "error": "query must not be empty"}
    return _run(["count", query, "--json"])


@mcp.tool(
    title="Show HiringCafe job",
    description="Retrieve full structured details for one HiringCafe object ID.",
    annotations=READ_ONLY,
)
def show_job(object_id: str) -> Any:
    object_id = object_id.strip()
    if not object_id:
        return {"ok": False, "error": "object_id must not be empty"}
    return _run(["job", "show", object_id, "--json"])


@mcp.tool(
    title="List HiringCafe saved jobs",
    description=(
        "List the authenticated user's HiringCafe saved-job board and stages. "
        "Requires HiringCafe credentials in the server environment."
    ),
    annotations=READ_ONLY,
)
def list_saved_jobs() -> Any:
    return _run(["saved-jobs", "list", "--json"])


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
