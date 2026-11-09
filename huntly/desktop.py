"""The Windows window for the same authenticated dashboard used in browsers."""

import asyncio
import ctypes
import logging
import socket
import sys
import webbrowser
from pathlib import Path
from threading import Thread
from time import monotonic, sleep
from urllib.parse import urlsplit

from huntly import dashboard_instance, home
from huntly.paths import PROJECT_ROOT

HOST = "127.0.0.1"
PORT = 5556


def open_gmail_draft(url: str) -> bool:
    """Open a marked manual draft in the browser where Gmail is signed in."""
    target = urlsplit(url)
    if (target.scheme, target.netloc, target.path) != ("https", "mail.google.com", "/mail/"):
        return False
    return webbrowser.open(url)


def _open_window(data_dir: Path) -> None:
    import uvicorn
    import webview

    from huntly import dashboard
    from huntly.state import StateManager

    with socket.socket() as listener:
        listener.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        try:
            listener.bind((HOST, PORT))
        except OSError as exc:
            raise RuntimeError(
                "Close any other Huntly desktop window, then try again."
            ) from exc

        asyncio.run(StateManager().init_db())
        server = uvicorn.Server(uvicorn.Config(
            dashboard.app, log_level="warning", access_log=False,
            proxy_headers=False, server_header=False, date_header=False,
            timeout_graceful_shutdown=3,
        ))
        url = dashboard.dashboard_url(HOST, PORT)
        thread = Thread(target=server.run, kwargs={"sockets": [listener]}, daemon=True)
        thread.start()
        try:
            deadline = monotonic() + 10
            while not server.started:
                if not thread.is_alive() or monotonic() >= deadline:
                    raise RuntimeError("Huntly's local dashboard could not start.")
                sleep(0.05)

            dashboard_instance.write(
                data_dir, host=HOST, port=PORT, instance=dashboard.INSTANCE_ID,
            )
            webview.settings["ALLOW_DOWNLOADS"] = True
            window = webview.create_window(
                "Huntly", url, width=1320, height=850, min_size=(420, 560),
            )
            window.expose(open_gmail_draft)
            webview.start(
                gui="edgechromium", private_mode=False, storage_path=str(data_dir / "webview"),
            )
        finally:
            server.should_exit = True
            thread.join(timeout=5)
            dashboard_instance.remove(data_dir, instance=dashboard.INSTANCE_ID)


def main() -> int:
    data_dir = PROJECT_ROOT / "data"
    log_path = data_dir / "desktop.log"
    try:
        home.seed_home(PROJECT_ROOT, home.bundled_defaults())
        with log_path.open("a", encoding="utf-8", buffering=1) as log:
            # A Windows GUI executable has no standard streams by default.
            stdout, stderr = sys.stdout, sys.stderr
            sys.stdout, sys.stderr = stdout or log, stderr or log
            try:
                _open_window(data_dir)
            except Exception:
                logging.getLogger(__name__).exception("Huntly desktop failed")
                raise
            finally:
                sys.stdout, sys.stderr = stdout, stderr
    except Exception as exc:
        detail = str(exc) if isinstance(exc, RuntimeError) else "Check the desktop log for details."
        ctypes.windll.user32.MessageBoxW(None, f"{detail}\n\n{log_path}", "Huntly", 0x10)
        return 1
    return 0
