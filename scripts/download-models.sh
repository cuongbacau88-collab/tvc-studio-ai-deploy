#!/bin/bash

set -Eeuo pipefail

# TVC Studio AI - Model Download Script
# Downloads model weights from Hugging Face
# Requires: huggingface-hub package

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="${SCRIPT_DIR}/.."

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

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

# Load environment variables
if [[ -f "${REPO_ROOT}/.env" ]]; then
    source "${REPO_ROOT}/.env"
fi

# Set default paths if not defined
MODELS_DIR="${MODELS_DIR:-.}/models"
WEIGHTS_DIR="${WEIGHTS_DIR:-.}/weights"

log_header "TVC Studio AI - Model Downloader"

# Check if huggingface-hub is installed
log_info "Checking for huggingface-hub package..."
if ! python3 -c "import huggingface_hub" 2>/dev/null; then
    log_warn "huggingface-hub not installed. Installing..."
    pip install huggingface-hub || {
        log_error "Failed to install huggingface-hub. Please install it manually:"
        log_error "  pip install huggingface-hub"
        exit 1
    }
fi

# Function to download model from HuggingFace
download_model() {
    local repo_id=$1
    local local_dir=$2
    local model_name=$3

    log_info "Downloading $model_name from $repo_id..."

    mkdir -p "$local_dir"

    python3 << EOF
import os
from huggingface_hub import snapshot_download

try:
    snapshot_download(
        repo_id="${repo_id}",
        local_dir="${local_dir}",
        local_dir_use_symlinks=False,
        resume_download=True,
        token=None  # Use HF_TOKEN env variable if authentication is needed
    )
    print("[SUCCESS] Downloaded to: ${local_dir}")
except Exception as e:
    print(f"[ERROR] Failed to download: {e}")
    exit(1)
EOF

    if [[ $? -eq 0 ]]; then
        log_info "$model_name downloaded successfully to $local_dir"
    else
        log_error "Failed to download $model_name"
        return 1
    fi
}

# Main menu
show_menu() {
    echo ""
    log_header "Available Models"
    echo "1) SCAIL-2 (zai-org/SCAIL-2)"
    echo "2) Wan2.2-Animate-14B (Wan-AI/Wan2.2-Animate-14B)"
    echo "3) Both SCAIL-2 and Wan2.2-Animate-14B"
    echo "4) Exit"
    echo ""
    read -p "Select model(s) to download (1-4): " choice
}

# Process selection
process_selection() {
    case "$choice" in
        1)
            download_model "zai-org/SCAIL-2" \
                "${MODELS_DIR}/scail2" \
                "SCAIL-2"
            ;;
        2)
            download_model "Wan-AI/Wan2.2-Animate-14B" \
                "${MODELS_DIR}/wan22-animate" \
                "Wan2.2-Animate-14B"
            ;;
        3)
            download_model "zai-org/SCAIL-2" \
                "${MODELS_DIR}/scail2" \
                "SCAIL-2"

            # Add small delay between downloads
            sleep 2

            download_model "Wan-AI/Wan2.2-Animate-14B" \
                "${MODELS_DIR}/wan22-animate" \
                "Wan2.2-Animate-14B"
            ;;
        4)
            log_info "Exiting downloader."
            exit 0
            ;;
        *)
            log_error "Invalid selection. Please choose 1-4."
            return 1
            ;;
    esac
}

# Main loop
while true; do
    show_menu
    if process_selection; then
        read -p "Download another model? (y/n): " continue_choice
        if [[ "$continue_choice" != "y" && "$continue_choice" != "Y" ]]; then
            break
        fi
    fi
done

log_header "Download Summary"
log_info "Models directory: $MODELS_DIR"

if [[ -d "${MODELS_DIR}/scail2" ]]; then
    scail_size=$(du -sh "${MODELS_DIR}/scail2" 2>/dev/null | cut -f1)
    log_info "SCAIL-2: $scail_size"
fi

if [[ -d "${MODELS_DIR}/wan22-animate" ]]; then
    wan_size=$(du -sh "${MODELS_DIR}/wan22-animate" 2>/dev/null | cut -f1)
    log_info "Wan2.2-Animate-14B: $wan_size"
fi

log_info "Download process completed!"
echo ""
echo "Next steps:"
echo "1. Review your .env file to ensure model paths are correct"
echo "2. Run your application to verify model loading"
echo ""
