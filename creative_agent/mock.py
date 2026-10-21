"""Start the mock PicLumen API (from the reference repo) on a free local port."""

from __future__ import annotations

import contextlib
import os
import socket
import subprocess
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MOCK_ENTRY = ROOT / "mcp" / "piclumen-api-mock" / "dist" / "server.js"
MCP_ENTRY = ROOT / "mcp" / "piclumen-mcp-server" / "dist" / "index.js"


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@contextlib.contextmanager
def mock_api(fast: bool = True):
    """Yield the mock's base URL. `fast` shortens the simulated job lifecycle."""
    if not MOCK_ENTRY.exists():
        raise SystemExit("Mock API not built. Run: make setup")
    port = _free_port()
    env = {**os.environ, "PORT": str(port)}
    if fast:
        env |= {"MOCK_QUEUED_MS": "200", "MOCK_PROCESSING_MS": "800"}
    proc = subprocess.Popen(["node", str(MOCK_ENTRY)], env=env,
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    base = f"http://127.0.0.1:{port}"
    try:
        for _ in range(50):
            try:
                urllib.request.urlopen(f"{base}/healthz", timeout=1)
                break
            except OSError:
                time.sleep(0.1)
        else:
            raise RuntimeError("mock API did not start")
        yield f"{base}/v1"
    finally:
        proc.terminate()
        proc.wait(timeout=5)
