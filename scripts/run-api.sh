#!/bin/bash
set -Eeuo pipefail

# One server process is mandatory: it owns the one shared sequential GPU queue.
# Binds to 0.0.0.0:8000 with 1 worker to process GPU jobs sequentially without VRAM congestion.
exec python3 -m uvicorn tvc_api.main:app --host "${API_HOST:-0.0.0.0}" --port "${PORT:-${API_PORT:-8000}}" --workers 1
