from __future__ import annotations

import unittest


class ServerImportTests(unittest.TestCase):
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
