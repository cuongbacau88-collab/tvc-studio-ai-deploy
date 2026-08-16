#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd)"
RUNTIME_ROOT="${TVC_RUNTIME_ROOT:-${REPO_ROOT}/runtime}"
COMFYUI_DIR="${COMFYUI_DIR:-${RUNTIME_ROOT}/ComfyUI}"
MANIFEST="${REPO_ROOT}/configs/custom_nodes_manifest.json"
MODEL_MANIFEST="${REPO_ROOT}/configs/model_manifest.json"

readarray -t COMFY_PIN < <(python3 - "${MANIFEST}" <<'PY'
import json, sys
d = json.load(open(sys.argv[1], encoding="utf-8"))["comfyui"]
print(d["repository"])
print(d["commit"])
PY
)
COMFY_REPO="${COMFY_PIN[0]}"
COMFY_COMMIT="${COMFY_PIN[1]}"

for command in git python3 nvidia-smi; do
  command -v "${command}" >/dev/null || { echo "ERROR: missing command: ${command}" >&2; exit 1; }
done
nvidia-smi >/dev/null || { echo "ERROR: NVIDIA GPU/driver is unavailable" >&2; exit 1; }

mkdir -p "${RUNTIME_ROOT}"
if [[ ! -d "${COMFYUI_DIR}/.git" ]]; then
  [[ ! -e "${COMFYUI_DIR}" ]] || { echo "ERROR: ${COMFYUI_DIR} exists but is not a git checkout" >&2; exit 1; }
  git clone --filter=blob:none "${COMFY_REPO}" "${COMFYUI_DIR}"
fi

actual_origin="$(git -C "${COMFYUI_DIR}" remote get-url origin)"
[[ "${actual_origin%.git}" == "${COMFY_REPO%.git}" ]] || {
  echo "ERROR: unexpected ComfyUI origin: ${actual_origin}" >&2
  exit 1
}
git -C "${COMFYUI_DIR}" fetch --depth 1 origin "${COMFY_COMMIT}"
git -C "${COMFYUI_DIR}" checkout --detach "${COMFY_COMMIT}"
[[ "$(git -C "${COMFYUI_DIR}" rev-parse HEAD)" == "${COMFY_COMMIT}" ]] || exit 1

python3 -m venv "${COMFYUI_DIR}/.venv"
"${COMFYUI_DIR}/.venv/bin/python" -m pip install --upgrade pip
"${COMFYUI_DIR}/.venv/bin/python" -m pip install -r "${COMFYUI_DIR}/requirements.txt"

python3 - "${MANIFEST}" "${COMFYUI_DIR}/custom_nodes" "${COMFYUI_DIR}/.venv/bin/python" <<'PY'
import json, pathlib, subprocess, sys
manifest = json.load(open(sys.argv[1], encoding="utf-8"))
root = pathlib.Path(sys.argv[2])
venv_python = sys.argv[3]
root.mkdir(parents=True, exist_ok=True)
packages = {}
for node in manifest["nodes"]:
    if node["classification"] != "custom":
        continue
    if node.get("source_status") != "resolved" or not node.get("repository") or not node.get("commit"):
        if node.get("required"):
            raise SystemExit(f"ERROR: unresolved required custom node {node['class_type']}")
        continue
    packages[(node["repository"], node["commit"])] = node.get("package") or node["class_type"]
for (repo, commit), package in packages.items():
    target = root / package.replace("/", "_")
    if not (target / ".git").is_dir():
        subprocess.run(["git", "clone", "--filter=blob:none", repo, str(target)], check=True)
    subprocess.run(["git", "-C", str(target), "fetch", "--depth", "1", "origin", commit], check=True)
    subprocess.run(["git", "-C", str(target), "checkout", "--detach", commit], check=True)
    requirements = target / "requirements.txt"
    if requirements.is_file():
        subprocess.run([venv_python, "-m", "pip", "install", "-r", str(requirements)], check=True)
PY

python3 - "${MODEL_MANIFEST}" "${COMFYUI_DIR}" <<'PY'
import json, pathlib, sys
manifest = json.load(open(sys.argv[1], encoding="utf-8"))
root = pathlib.Path(sys.argv[2]).resolve()
for model in manifest["models"]:
    destination = (root / model["comfyui_subdir"]).resolve()
    if root not in destination.parents:
        raise SystemExit(f"ERROR: unsafe model directory: {destination}")
    destination.mkdir(parents=True, exist_ok=True)
PY

echo "ComfyUI bootstrap complete at ${COMFYUI_DIR}"
echo "Models were NOT downloaded and ComfyUI was NOT started."
