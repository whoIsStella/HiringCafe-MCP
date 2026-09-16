from __future__ import annotations

import unittest


class ServerImportTests(unittest.TestCase):
    def test_server_imports_and_registers_tools(self) -> None:
        from hiringcafe_mcp.server import mcp

        self.assertIsNotNone(mcp)


if __name__ == "__main__":
    unittest.main()
