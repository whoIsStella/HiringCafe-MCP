from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass
from typing import Any, Sequence


@dataclass(slots=True)
class HiringCafeError(RuntimeError):
    message: str
    exit_code: int | None = None
    stderr: str = ""

    def __str__(self) -> str:
        suffix = f" (exit {self.exit_code})" if self.exit_code is not None else ""
        detail = f": {self.stderr.strip()}" if self.stderr.strip() else ""
        return f"{self.message}{suffix}{detail}"


def _binary() -> str:
    binary = shutil.which("hiringcafe")
    if not binary:
        raise HiringCafeError(
            "hiringcafe executable not found; install hiringcafe-cli==0.1.5"
        )
    return binary


def run_json(args: Sequence[str], *, timeout: int = 60) -> Any:
    """Run a hiringcafe CLI command without a shell and parse JSON stdout."""
    cmd = [_binary(), *args]
    try:
        proc = subprocess.run(
            cmd,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        raise HiringCafeError("HiringCafe command timed out") from exc

    if proc.returncode != 0:
        messages = {
            1: "HiringCafe transport/API error",
            2: "Invalid HiringCafe arguments/search state",
            3: "HiringCafe rate limit reached",
            4: "HiringCafe authentication required",
            5: "Stored HiringCafe credential was rejected; re-authenticate",
            6: "HiringCafe conflict or prerequisite missing; refresh state",
        }
        raise HiringCafeError(
            messages.get(proc.returncode, "HiringCafe command failed"),
            exit_code=proc.returncode,
            stderr=proc.stderr,
        )

    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise HiringCafeError(
            "HiringCafe returned non-JSON output",
            exit_code=proc.returncode,
            stderr=proc.stderr,
        ) from exc
