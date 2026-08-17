"""Railpack-compatible ASGI entrypoint for the TVC Studio API."""

import os

import uvicorn

from tvc_api.main import app


if __name__ == "__main__":
    # Keep a single process because it owns the shared sequential GPU queue.
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "8000")), workers=1)
