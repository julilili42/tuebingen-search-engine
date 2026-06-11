"""Spotlight-style desktop launcher.

Serves the existing FastAPI app on a local port and opens the Spotlight UI
in a frameless, translucent desktop window (pywebview, optional dependency).
Without pywebview the UI opens in the default browser instead.
"""

from __future__ import annotations

import argparse
import logging
import os
import socket
import threading
import time
import webbrowser

import httpx
import uvicorn

logger = logging.getLogger(__name__)

WINDOW_WIDTH = 1000
WINDOW_HEIGHT = 640
STARTUP_TIMEOUT = 30.0


class SpotlightApi:
    """Bridge for JS calls from inside the desktop window."""

    def __init__(self) -> None:
        self.window = None

    def open_url(self, url: str) -> None:
        webbrowser.open(url)

    def close(self) -> None:
        if self.window is not None:
            self.window.destroy()


def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def start_server(index_path: str, port: int) -> threading.Thread:
    os.environ["INDEX_PATH"] = index_path
    from .api import app  # imported late so INDEX_PATH is set first

    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    return thread


def wait_until_ready(url: str) -> None:
    deadline = time.monotonic() + STARTUP_TIMEOUT
    while time.monotonic() < deadline:
        try:
            if httpx.get(url, timeout=2.0).status_code == 200:
                return
        except httpx.HTTPError:
            pass
        time.sleep(0.1)
    raise RuntimeError("search API did not start in time")


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    parser = argparse.ArgumentParser(
        prog="tuebingen-desktop",
        description="Open the Tübingen Search Spotlight window.",
    )
    parser.add_argument("-i", "--index", default="index.bin")
    args = parser.parse_args()

    port = free_port()
    start_server(args.index, port)
    wait_until_ready(f"http://127.0.0.1:{port}/health")
    # The shell parameter tells the page it runs inside the frameless window
    # (window.pywebview is injected only after page load, so the page cannot
    # detect that reliably on its own).
    spotlight_url = f"http://127.0.0.1:{port}/spotlight?shell=desktop"

    try:
        import webview
    except ImportError:
        logger.info(
            "pywebview is not installed (uv sync --extra desktop); "
            "opening %s in the browser instead", spotlight_url,
        )
        webbrowser.open(spotlight_url)
        try:
            while True:
                time.sleep(3600)
        except KeyboardInterrupt:
            return

    api = SpotlightApi()
    api.window = webview.create_window(
        "Tübingen Search",
        url=spotlight_url,
        js_api=api,
        width=WINDOW_WIDTH,
        height=WINDOW_HEIGHT,
        frameless=True,
        easy_drag=True,
        transparent=True,
        on_top=True,
    )
    webview.start()


if __name__ == "__main__":
    main()
