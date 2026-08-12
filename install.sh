#!/bin/bash

set -Eeuo pipefail

# TVC Studio AI - Installation Script
# For Ubuntu 22.04 and 24.04
# Installs SCAIL 2 and Wan2.2 with separate virtual environments

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ALLOW_FLASHATTENTION="${ALLOW_FLASHATTENTION:-0}"
PYTHON_VERSION="${PYTHON_VERSION:-3.11}"

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

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

# Trap errors and display helpful message
trap 'log_error "Installation failed at line $LINENO. Check the output above for details."' ERR

# Step 1: Run preflight checks
log_info "Running preflight checks..."
if [[ -f "${SCRIPT_DIR}/scripts/preflight.sh" ]]; then
    bash "${SCRIPT_DIR}/scripts/preflight.sh" || {
        log_error "Preflight checks failed. Please fix the issues before proceeding."
        exit 1
    }
else
    log_error "preflight.sh not found. Please ensure scripts/preflight.sh exists."
    exit 1
fi

# Step 1b: Run GPU checks (multi-GPU support validation)
log_info "Checking GPU setup for multi-GPU support..."
if [[ -f "${SCRIPT_DIR}/scripts/gpu-check.sh" ]]; then
    bash "${SCRIPT_DIR}/scripts/gpu-check.sh" || {
        log_warn "GPU check reported issues (see above). Continuing with installation."
    }
else
    log_warn "gpu-check.sh not found. Skipping GPU validation."
fi

# Step 2: Check Python version
log_info "Checking Python installation..."
if ! command -v python3 &> /dev/null; then
    log_error "Python3 is not installed. Please install Python 3.10+ first."
    exit 1
fi

PYTHON_PATH=$(command -v python3)
PYTHON_INSTALLED_VERSION=$("${PYTHON_PATH}" --version 2>&1 | awk '{print $2}')
log_info "Found Python: ${PYTHON_INSTALLED_VERSION}"

# Step 3: Install system dependencies
log_info "Installing system dependencies..."
sudo apt-get update -qq
sudo apt-get install -y \
    python3-venv \
    python3-dev \
    build-essential \
    git \
    wget \
    curl \
    libssl-dev \
    libffi-dev \
    libopenblas-dev \
    2>&1 | grep -v "^Get:" | grep -v "^Reading" | grep -v "^Building" || true

log_info "System dependencies installed successfully."

# Step 4: Clone SCAIL-2 repository (with 404 fallback)
log_info "Cloning SCAIL-2 repository..."
SCAIL_DIR="${SCRIPT_DIR}/repos/SCAIL-2"
if [[ -d "${SCAIL_DIR}" ]]; then
    log_warn "SCAIL-2 directory already exists at ${SCAIL_DIR}. Skipping clone."
else
    mkdir -p "${SCRIPT_DIR}/repos"
    # Attempt clone with fallback for 404 error (repository inaccessible)
    if git clone https://github.com/zai-org/SCAIL-2.git "${SCAIL_DIR}" 2>&1 | grep -q "404\|not found"; then
        log_warn "SCAIL-2 repository not accessible (HTTP 404). See docs/scail2-workaround.md"
        log_warn "Continuing installation without SCAIL-2. This is optional."
            [[ -n "$SCAIL_DIR" && "$SCAIL_DIR" == "$SCRIPT_DIR"/repos/* && "$SCAIL_DIR" != "$SCRIPT_DIR/repos" ]] || { log_error "Unsafe SCAIL_DIR: $SCAIL_DIR"; exit 1; }
        rm -rf "${SCAIL_DIR}"  # Clean up failed clone
        SCAIL_CLONE_FAILED=1
    elif [[ ! -d "${SCAIL_DIR}" ]]; then
        log_error "Failed to clone SCAIL-2 repository."
        exit 1
    else
        log_info "SCAIL-2 cloned successfully."
        SCAIL_CLONE_FAILED=0
    fi
fi

# Step 5: Clone Wan2.2 repository
log_info "Cloning Wan2.2 repository..."
WAN_DIR="${SCRIPT_DIR}/repos/Wan2.2"
if [[ -d "${WAN_DIR}" ]]; then
    log_warn "Wan2.2 directory already exists at ${WAN_DIR}. Skipping clone."
else
    mkdir -p "${SCRIPT_DIR}/repos"
    git clone https://github.com/Wan-Video/Wan2.2.git "${WAN_DIR}" || {
        log_error "Failed to clone Wan2.2 repository."
        exit 1
    }
    log_info "Wan2.2 cloned successfully."
fi

# Step 6: Setup SCAIL-2 virtual environment (skip if clone failed)
if [[ "${SCAIL_CLONE_FAILED:-0}" == "1" ]]; then
    log_warn "Skipping SCAIL-2 venv setup (repository not accessible)"
else
    log_info "Setting up SCAIL-2 Python environment..."
SCAIL_VENV="${SCRIPT_DIR}/venv/scail2"
if [[ -d "${SCAIL_VENV}" ]]; then
    log_warn "SCAIL-2 venv already exists. Skipping creation."
else
    "${PYTHON_PATH}" -m venv "${SCAIL_VENV}" || {
        log_error "Failed to create SCAIL-2 virtual environment."
        exit 1
    }
    log_info "SCAIL-2 venv created at ${SCAIL_VENV}"
fi

# Activate SCAIL-2 venv and upgrade pip
source "${SCAIL_VENV}/bin/activate"
log_info "Upgrading pip for SCAIL-2..."
pip install --upgrade pip setuptools wheel -q

# Install PyTorch for SCAIL-2
log_info "Installing PyTorch for SCAIL-2..."
# Check for GPU
if command -v nvidia-smi &> /dev/null; then
    log_info "GPU detected. Installing CUDA-enabled PyTorch..."
    pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118 -q 2>&1 | tail -1
else
    log_warn "No GPU detected. Installing CPU-only PyTorch..."
    pip install torch torchvision torchaudio -q 2>&1 | tail -1
fi

# Install SCAIL-2 requirements
if [[ -f "${SCAIL_DIR}/requirements.txt" ]]; then
    log_info "Installing SCAIL-2 requirements..."
    pip install -r "${SCAIL_DIR}/requirements.txt" -q 2>&1 | tail -1
else
    log_warn "SCAIL-2 requirements.txt not found. Skipping."
fi

# Install FlashAttention for SCAIL-2 if allowed
if [[ "${ALLOW_FLASHATTENTION}" == "1" ]]; then
    log_info "Installing FlashAttention for SCAIL-2..."
    pip install flash-attn -q 2>&1 | tail -1 || {
        log_warn "FlashAttention installation failed. Continuing without it."
    }
else
    log_info "FlashAttention installation skipped. Set ALLOW_FLASHATTENTION=1 to enable."
fi

    deactivate
fi

# Step 7: Setup Wan2.2 virtual environment
log_info "Setting up Wan2.2 Python environment..."
WAN_VENV="${SCRIPT_DIR}/venv/wan22"
if [[ -d "${WAN_VENV}" ]]; then
    log_warn "Wan2.2 venv already exists. Skipping creation."
else
    "${PYTHON_PATH}" -m venv "${WAN_VENV}" || {
        log_error "Failed to create Wan2.2 virtual environment."
        exit 1
    }
    log_info "Wan2.2 venv created at ${WAN_VENV}"
fi

# Activate Wan2.2 venv and upgrade pip
source "${WAN_VENV}/bin/activate"
log_info "Upgrading pip for Wan2.2..."
pip install --upgrade pip setuptools wheel -q

# Install PyTorch for Wan2.2
log_info "Installing PyTorch for Wan2.2..."
# Check for GPU
if command -v nvidia-smi &> /dev/null; then
    log_info "GPU detected. Installing CUDA-enabled PyTorch..."
    pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118 -q 2>&1 | tail -1
else
    log_warn "No GPU detected. Installing CPU-only PyTorch..."
    pip install torch torchvision torchaudio -q 2>&1 | tail -1
fi

# Install Wan2.2 requirements
if [[ -f "${WAN_DIR}/requirements.txt" ]]; then
    log_info "Installing Wan2.2 requirements..."
    pip install -r "${WAN_DIR}/requirements.txt" -q 2>&1 | tail -1
else
    log_warn "Wan2.2 requirements.txt not found. Skipping."
fi

# Install FlashAttention for Wan2.2 if allowed
if [[ "${ALLOW_FLASHATTENTION}" == "1" ]]; then
    log_info "Installing FlashAttention for Wan2.2..."
    pip install flash-attn -q 2>&1 | tail -1 || {
        log_warn "FlashAttention installation failed. Continuing without it."
    }
else
    log_info "FlashAttention installation skipped. Set ALLOW_FLASHATTENTION=1 to enable."
fi

deactivate

# Step 8: Create environment configuration
log_info "Creating .env file if not exists..."
if [[ ! -f "${SCRIPT_DIR}/.env" ]]; then
    cp "${SCRIPT_DIR}/.env.example" "${SCRIPT_DIR}/.env"
    log_info ".env created from .env.example"
else
    log_info ".env already exists. Skipping."
fi

log_info "Installation completed successfully!"
log_info ""
if [[ "${SCAIL_CLONE_FAILED:-0}" == "1" ]]; then
    log_warn "Note: SCAIL-2 repository inaccessible. See docs/scail2-workaround.md"
    log_info ""
fi
log_info "Next steps:"
log_info "1. Run: bash ${SCRIPT_DIR}/scripts/model-selector.sh (GPU recommendation tool)"
log_info "2. Edit ${SCRIPT_DIR}/.env with your configuration"
log_info "3. Run ${SCRIPT_DIR}/scripts/download-models.sh to download core models (if Wan2.2 available)"
log_info "4. Review ${SCRIPT_DIR}/README.md for usage instructions"
log_info ""
log_info "Optional: Install additional AI services (image editing, enhancement, etc.):"
log_info "  - Run: bash ${SCRIPT_DIR}/scripts/model-selector.sh (recommended for your GPU)"
log_info "  - Install a model: bash ${SCRIPT_DIR}/scripts/install-model.sh <model-name>"
log_info "  - Verify install: bash ${SCRIPT_DIR}/scripts/health-check.sh <model-name>"
log_info "  - Download weights: bash ${SCRIPT_DIR}/scripts/download-model.sh <model-name>"
log_info ""
log_info "Validation tools:"
log_info "  - Manifest validation: bash ${SCRIPT_DIR}/tests/validate-manifest.sh"
log_info "  - GPU capability: bash ${SCRIPT_DIR}/scripts/gpu-check.sh"
log_info "  - Health check: bash ${SCRIPT_DIR}/scripts/health-check.sh"
log_info ""
log_info "Available models:"
log_info "  Video Generation: wan22-animate (image-to-video)"
log_info "  Image Try-On: fashn-vton"
log_info "  Scene Editing: qwen-image-edit (+ optional: birefnet, ic-light)"
log_info "  Enhancement: seedvr2, realesrgan, codeformer"
log_info ""
log_info "Documentation:"
log_info "  - Model specs: docs/model-matrix.md"
log_info "  - GPU strategies: docs/gpu-strategies.md"
log_info "  - Architecture: docs/deployment-architecture.md"
log_info "  - SCAIL-2 issue: docs/scail2-workaround.md"
log_info ""
