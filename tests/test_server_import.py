from __future__ import annotations

import unittest
from unittest.mock import patch


class ServerImportTests(unittest.TestCase):
    def test_cli_envelope_is_compacted_before_caching(self) -> None:
        from hiringcafe_mcp import server
        from hiringcafe_mcp.cache import ReadCache

        envelope = {
            "version": 1,
            "query": {"searchState": {"searchQuery": "backend"}, "page": 0},
            "result": {
                "totalCount": 200, "page": 0, "isLastPage": False,
                "jobs": [{"id": str(i), "title": "Engineer", "source": "example",
                          "publishedAt": "2026-10-01", "expired": False,
                          "description": "x" * 10000} for i in range(25)],
            },
        }
        cache = ReadCache()
        with patch.object(server, "_reads", cache), patch.object(
            server, "run_json", return_value=envelope,
        ) as cli:
            first = server.search_jobs("backend")
            second = server.search_jobs("backend")
        cli.assert_called_once()
        self.assertEqual(first, second)
        self.assertEqual(first["query"], envelope["query"])
        self.assertEqual(first["result"]["totalCount"], 200)
        self.assertEqual(first["result"]["returned_jobs"], 20)
        self.assertTrue(first["result"]["truncated"])
        self.assertNotIn("description", first["result"]["jobs"][0])
        self.assertEqual(first["result"]["jobs"][0]["publishedAt"], "2026-10-01")
        self.assertLess(cache.size, 10000)
        self.assertEqual(len(envelope["result"]["jobs"]), 25)

    def test_server_imports_and_registers_tools(self) -> None:
        from hiringcafe_mcp.server import mcp

        self.assertIsNotNone(mcp)

    def test_diagnostic_error_is_structured(self) -> None:
        from hiringcafe_mcp.cli import HiringCafeError
        from hiringcafe_mcp.server import _diagnostic_error

        result = _diagnostic_error(
            HiringCafeError("HiringCafe transport/API error", exit_code=1, stderr="boom")
        )
        self.assertEqual(result["ok"], False)
        self.assertEqual(result["exit_code"], 1)
        self.assertEqual(result["stderr"], "boom")

    def test_compact_search_limits_and_strips_large_fields(self) -> None:
        from hiringcafe_mcp.server import _compact_search

        result = _compact_search(
            {
                "jobs": [
                    {
                        "objectID": str(i),
                        "title": f"Engineer {i}",
                        "company": "Example",
                        "description": "x" * 10000,
                    }
                    for i in range(25)
                ]
            },
            max_jobs=20,
        )
        self.assertEqual(result["returned_jobs"], 20)
        self.assertEqual(result["available_in_page"], 25)
        self.assertTrue(result["truncated"])
        self.assertNotIn("description", result["jobs"][0])


if __name__ == "__main__":
    unittest.main()
