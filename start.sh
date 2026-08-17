#!/bin/bash

set -Eeuo pipefail

# One server process is mandatory: it owns the one shared sequential GPU queue.
exec python3 -m uvicorn tvc_api.main:app --host 0.0.0.0 --port "${PORT:-8000}" --workers 1
