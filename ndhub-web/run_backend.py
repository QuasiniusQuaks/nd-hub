#!/usr/bin/env python3
"""Start script for ND-Hub FastAPI backend."""

from __future__ import annotations

import os

import uvicorn


def main() -> None:
    host = os.environ.get("ND_HUB_BACKEND_HOST", "127.0.0.1")
    port = int(os.environ.get("ND_HUB_BACKEND_PORT", "8000"))
    uvicorn.run(
        "backend.app:app",
        host=host,
        port=port,
        reload=False,
    )


if __name__ == "__main__":
    main()

