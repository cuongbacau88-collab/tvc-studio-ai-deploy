#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd)"
export COMFYUI_DIR="${COMFYUI_DIR:-${TVC_RUNTIME_ROOT:-${REPO_ROOT}/runtime}/ComfyUI}"
export COMFYUI_URL="${COMFYUI_URL:-http://127.0.0.1:8188}"
COMFYUI_PORT="${COMFYUI_PORT:-8188}"

"${SCRIPT_DIR}/bootstrap_vast.sh"
"${SCRIPT_DIR}/download-models.sh" --comfyui-root "${COMFYUI_DIR}"

mkdir -p "${COMFYUI_DIR}/user"
"${COMFYUI_DIR}/.venv/bin/python" "${COMFYUI_DIR}/main.py" \
  --listen 127.0.0.1 --port "${COMFYUI_PORT}" \
  >"${COMFYUI_DIR}/comfyui.log" 2>&1 &
COMFYUI_PID=$!
echo "${COMFYUI_PID}" >"${COMFYUI_DIR}/comfyui.pid"

ready=0
for _ in $(seq 1 120); do
  if curl --fail --silent "${COMFYUI_URL}/object_info" >/dev/null; then
    ready=1
    break
  fi
  if ! kill -0 "${COMFYUI_PID}" 2>/dev/null; then
    echo "ERROR: ComfyUI stopped during startup; inspect ${COMFYUI_DIR}/comfyui.log" >&2
    exit 1
  fi
  sleep 2
done
[[ "${ready}" == 1 ]] || { echo "ERROR: ComfyUI did not become ready" >&2; exit 1; }

exec "${COMFYUI_DIR}/.venv/bin/python" "${SCRIPT_DIR}/runtime_preflight.py" \
  --comfyui-dir "${COMFYUI_DIR}" --comfyui-url "${COMFYUI_URL}"
