"""Run PocketSmart AI locally: python run.py"""
import os
import socket
import sys

import uvicorn

from app.core.config import settings

HOST = "127.0.0.1"
PORT = int(os.environ.get("PORT", "8000"))


def _port_in_use(host: str, port: int) -> bool:
    """True when something already listens on host:port (e.g. an older instance)."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.settimeout(2)
        return probe.connect_ex((host, port)) == 0


if __name__ == "__main__":
    if _port_in_use(HOST, PORT):
        print(
            f"ERROR: {HOST}:{PORT} is already in use — another PocketSmart AI "
            f"instance (or another app) is still running there.\n"
            f"  - Stop the old instance and run `python run.py` again, or\n"
            f"  - Use a different port:  set PORT=8001  then  python run.py\n"
            f"The server was NOT started; no data was changed.",
            file=sys.stderr,
        )
        sys.exit(1)
    uvicorn.run(
        "app.main:app",
        host=HOST,
        port=PORT,
        reload=settings.DEBUG,
    )
