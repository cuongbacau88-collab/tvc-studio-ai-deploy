#!/bin/bash

set -Eeuo pipefail

# TVC Studio AI - Model Weights Downloader
# Downloads specific model weights from Hugging Face
# Usage: ./download-model.sh <model-name>
# Example: ./download-model.sh fashn-vton

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="${SCRIPT_DIR}/.."
MODELS_CONFIG="${REPO_ROOT}/configs/models.yaml"

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Logging functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $*"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $*"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $*"
}

log_header() {
    echo ""
    echo -e "${BLUE}=== $* ===${NC}"
}

# Error handler
trap 'log_error "Download failed at line $LINENO."' ERR

# Parse arguments
if [[ $# -lt 1 ]]; then
    log_error "Usage: $0 <model-name>"
    echo ""
    echo "Available models:"
    echo "  - scail2"
    echo "  - wan22-animate"
    echo "  - fashn-vton"
    echo "  - qwen-image-edit"
    echo "  - birefnet"
    echo "  - ic-light"
    echo "  - seedvr2"
    echo "  - realesrgan"
    echo "  - codeformer"
    exit 1
fi

MODEL_NAME="$1"

log_header "TVC Studio AI - Model Weights Downloader"
log_info "Target model: $MODEL_NAME"

# Function to parse YAML value (simple parser)
parse_yaml_value() {
    local file=$1
    local section=$2
    local key=$3

    grep -A 100 "^  $section:" "$file" | \
        grep "    $key:" | \
        head -1 | \
        sed "s/.*: //" | \
        sed 's/"//g' | \
        sed "s/'//g" || echo ""
}

# Check if model exists
if ! grep -q "^  $MODEL_NAME:" "$MODELS_CONFIG"; then
    log_error "Model '$MODEL_NAME' not found in $MODELS_CONFIG"
    exit 1
fi

# Extract model configuration
HF_MODEL=$(parse_yaml_value "$MODELS_CONFIG" "$MODEL_NAME" "huggingface_model")
WEIGHTS_DIR=$(parse_yaml_value "$MODELS_CONFIG" "$MODEL_NAME" "weights_dir")

if [[ -z "$HF_MODEL" ]]; then
    log_error "Could not parse Hugging Face model ID for: $MODEL_NAME"
    exit 1
fi

FULL_WEIGHTS_PATH="${REPO_ROOT}/${WEIGHTS_DIR}"

log_info "Hugging Face model: $HF_MODEL"
log_info "Local directory: $FULL_WEIGHTS_PATH"

# Check for huggingface-hub
log_header "Checking Dependencies"

if ! python3 -c "import huggingface_hub" 2>/dev/null; then
    log_warn "huggingface-hub package not installed."
    log_info "Installing huggingface-hub..."
    pip install huggingface-hub || {
        log_error "Failed to install huggingface-hub"
        exit 1
    }
fi

log_info "huggingface-hub verified"

# Check for HF_TOKEN if available
log_header "Authentication"
if [[ -n "${HF_TOKEN:-}" ]]; then
    log_info "Using HF_TOKEN from environment"
else
    log_warn "No HF_TOKEN set. Download of private models will fail."
    log_warn "Set HF_TOKEN if you need access to private models:"
    log_warn '  export HF_TOKEN="YOUR_HUGGING_FACE_TOKEN"'
fi

# Check disk space
log_header "Storage Check"

if [[ -d "$FULL_WEIGHTS_PATH" ]]; then
    CURRENT_SIZE=$(du -sh "$FULL_WEIGHTS_PATH" 2>/dev/null | cut -f1)
    log_warn "Weights directory already exists: $CURRENT_SIZE"
    read -p "Re-download and overwrite? (y/n): " overwrite_choice
    if [[ "$overwrite_choice" != "y" && "$overwrite_choice" != "Y" ]]; then
        log_info "Download cancelled."
        exit 0
    fi
fi

AVAILABLE_SPACE=$(df "$REPO_ROOT" | tail -1 | awk '{print $4}')
AVAILABLE_GB=$((AVAILABLE_SPACE / 1024 / 1024))
log_info "Available disk space: ${AVAILABLE_GB}GB"

if [[ $AVAILABLE_GB -lt 20 ]]; then
    log_warn "Limited disk space available (< 20GB)"
    log_warn "Model download may fail if file is larger than available space"
fi

# Download using Python
log_header "Downloading Model"

python3 << 'PYTHON_SCRIPT'
import os
import sys
from pathlib import Path

try:
    from huggingface_hub import snapshot_download
except ImportError:
    print("ERROR: huggingface-hub not available")
    sys.exit(1)

model_name = os.environ.get('MODEL_NAME', '')
hf_model = os.environ.get('HF_MODEL', '')
weights_dir = os.environ.get('FULL_WEIGHTS_PATH', '')
hf_token = os.environ.get('HF_TOKEN', None)

if not all([model_name, hf_model, weights_dir]):
    print("ERROR: Missing environment variables")
    sys.exit(1)

print(f"[INFO] Starting download of {hf_model}...")

try:
    Path(weights_dir).parent.mkdir(parents=True, exist_ok=True)

    snapshot_download(
        repo_id=hf_model,
        local_dir=weights_dir,
        local_dir_use_symlinks=False,
        resume_download=True,
        token=hf_token
    )

    print(f"[INFO] Download completed successfully!")
    print(f"[INFO] Model saved to: {weights_dir}")

    # Print directory size
    import subprocess
    result = subprocess.run(['du', '-sh', weights_dir], capture_output=True, text=True)
    print(f"[INFO] Total size: {result.stdout.strip()}")

except Exception as e:
    print(f"[ERROR] Download failed: {e}")
    sys.exit(1)
PYTHON_SCRIPT

# Store result
DOWNLOAD_SUCCESS=$?

if [[ $DOWNLOAD_SUCCESS -ne 0 ]]; then
    log_error "Model download failed"
    exit 1
fi

# Verify download
log_header "Verification"

if [[ -d "$FULL_WEIGHTS_PATH" ]]; then
    FILE_COUNT=$(find "$FULL_WEIGHTS_PATH" -type f | wc -l)
    TOTAL_SIZE=$(du -sh "$FULL_WEIGHTS_PATH" | cut -f1)
    log_info "✓ Download verified"
    log_info "  Files: $FILE_COUNT"
    log_info "  Size: $TOTAL_SIZE"
else
    log_error "Weights directory not found after download"
    exit 1
fi

# Summary
log_header "Download Complete"
log_info "Model: $MODEL_NAME"
log_info "Location: $FULL_WEIGHTS_PATH"
echo ""
echo "Next steps:"
echo "1. Verify the model is in the correct location"
echo "2. Update .env if needed to point to this location"
echo "3. Run health checks: bash scripts/health-check.sh"
echo ""
