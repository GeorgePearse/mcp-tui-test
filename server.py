#!/usr/bin/env python3
"""Back-compat shim: `python server.py` still works; the code lives in mcp_tui_test/."""

from mcp_tui_test.server import main, mcp  # noqa: F401 — mcp re-exported for older configs

if __name__ == "__main__":
    main()
