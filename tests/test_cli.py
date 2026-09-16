from __future__ import annotations

import os
import stat
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from hiringcafe_mcp.cli import HiringCafeError, run_json


class CliTests(unittest.TestCase):
    def _fake_cli(self, body: str) -> tuple[tempfile.TemporaryDirectory, str]:
        td = tempfile.TemporaryDirectory()
        path = Path(td.name) / "hiringcafe"
        path.write_text("#!/bin/sh\n" + body + "\n", encoding="utf-8")
        path.chmod(path.stat().st_mode | stat.S_IXUSR)
        return td, td.name

    def test_parses_json(self) -> None:
        td, bindir = self._fake_cli("printf '%s\\n' '{\"jobs\":[{\"id\":1}]}'")
        self.addCleanup(td.cleanup)
        with patch.dict(os.environ, {"PATH": bindir}):
            result = run_json(["search", "backend", "--json"])
        self.assertEqual(result["jobs"][0]["id"], 1)

    def test_maps_auth_error(self) -> None:
        td, bindir = self._fake_cli("echo 'login required' >&2; exit 4")
        self.addCleanup(td.cleanup)
        with patch.dict(os.environ, {"PATH": bindir}):
            with self.assertRaises(HiringCafeError) as ctx:
                run_json(["saved-jobs", "list", "--json"])
        self.assertEqual(ctx.exception.exit_code, 4)
        self.assertIn("authentication required", str(ctx.exception).lower())

    def test_rejects_non_json(self) -> None:
        td, bindir = self._fake_cli("echo not-json")
        self.addCleanup(td.cleanup)
        with patch.dict(os.environ, {"PATH": bindir}):
            with self.assertRaises(HiringCafeError) as ctx:
                run_json(["count", "backend", "--json"])
        self.assertIn("non-JSON", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
